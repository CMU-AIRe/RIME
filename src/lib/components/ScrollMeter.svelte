<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';

  /** The element whose scroll progress we track (e.g. "#article .md-output") */
  export let containerSelector = '.md-output';
  /** Which headings become ticks */
  export let headingsSelector = 'h2, h3';
  /** Max width for the TOC column (px) */
  export let tocMaxWidthCap = 320;

  type Heading = {
    id: string;
    level: 2 | 3;
    top: number;
    labelText: string;
    labelHtml: string;
    inSummary: boolean;
    inClosedDetails: boolean;
    el: HTMLElement;
  };

  let headings: Heading[] = [];
  let visibleHeadings: Heading[] = [];
  let showAll = true;
  let visibleIdSet: Set<string> | null = null;
  let active_index = -1;
  let container_el: HTMLElement | null = null;
  let ready = false;
  let raf_id: number;
  let hydrated = false;
  let isHovering = false;
  let hideToc = false;
  const SIDE_DATASET_KEY = "sidecols";
  let lastPublishedSide: "on" | "off" | null = null;
  let watchTimer: number | null = null;
  let lastWatchDpr = -1;
  let lastWatchVw = -1;
  let hideByWidth = false;
  let scrollRaf: number | null = null;
  // Cache TOC geometry so we can update only its left position on scroll (cheap),
  // which matters when the page can horizontally scroll under zoom.
  let lastTocWidth = 280;
  let lastTocGap = 32;
  let lastTocMinLeft = 16;

  function onTocWheel(e: WheelEvent) {
    if (!meterEl) return;
    // If the TOC is scrollable, use the wheel to scroll it and keep the page from scrolling.
    const max = meterEl.scrollHeight - meterEl.clientHeight;
    if (max <= 0) return;

    const prev = meterEl.scrollTop;
    const next = Math.max(0, Math.min(max, prev + e.deltaY));
    if (next === prev) return;

    meterEl.scrollTop = next;
    e.preventDefault();
    e.stopPropagation();
  }

  function syncTocMaxWidthCap() {
    if (!browser) return;
    const root = document.documentElement;
    root.style.setProperty("--toc-max-width-cap", `${tocMaxWidthCap}`);
  }

  function publishMainColWidthPx(px: number) {
    if (!browser) return;
    const root = document.documentElement;
    const v = `${Math.max(0, Math.round(px))}px`;
    root.style.setProperty("--md-main-col", v);
  }

  function publishSideCols(side: "on" | "off") {
    if (!browser) return;
    const root = document.documentElement;
    if (root?.dataset) root.dataset[SIDE_DATASET_KEY] = side;
    if (lastPublishedSide === side) return;
    lastPublishedSide = side;
    window.dispatchEvent(new CustomEvent("sidecolschange", { detail: { side } }));
  }

  function canHorizontallyScrollPage(): boolean {
    if (!browser) return false;
    const se = (document.scrollingElement || document.documentElement) as HTMLElement | null;
    if (!se) return false;
    const prev = se.scrollLeft;
    // Probe: if scrollLeft can change, horizontal scrolling is possible.
    se.scrollLeft = prev + 1;
    const changed = se.scrollLeft !== prev;
    se.scrollLeft = prev;
    return changed;
  }

  function doc_y(el: Element) {
    const r = el.getBoundingClientRect();
    return (browser ? window.scrollY : 0) + r.top;
  }

  function should_include_heading(h: HTMLElement) {
    if (h.hasAttribute('data-skip-meter')) return false;
    if (h.getAttribute('data-meter') === 'false') return false;
    if (h.classList.contains('no-meter')) return false;
    return true;
  }

  function effectiveTopForHeading(h: HTMLElement) {
    // If the heading is inside a collapsed <details>, its own rect is 0 (hidden).
    // Use the fold summary position as a stable proxy so the TOC can still compute
    // a monotonic ordering and clickable navigation works.
    const d = h.closest("details") as HTMLDetailsElement | null;
    if (d && !d.open) {
      const summary = d.querySelector("summary");
      if (summary) return doc_y(summary);
      return doc_y(d);
    }
    return doc_y(h);
  }

  function openParentFolds(el: HTMLElement) {
    let d = el.closest("details") as HTMLDetailsElement | null;
    while (d) {
      d.open = true;
      d = d.parentElement?.closest("details") as HTMLDetailsElement | null;
    }
  }

  function gotoHeading(id: string) {
    if (!browser) return;
    const root = container_el ?? document;
    const target = root.querySelector<HTMLElement>(`#${CSS.escape(id)}`);
    if (!target) {
      // Fallback: still update hash so other listeners can react.
      window.location.hash = `#${id}`;
      return;
    }
    // If the target is inside a closed fold, scroll to its summary first,
    // then open folds and finish the jump in the next frame.
    let firstClosed: HTMLDetailsElement | null = null;
    let d = target.closest("details") as HTMLDetailsElement | null;
    while (d) {
      if (!d.open) {
        firstClosed = d;
        break;
      }
      d = d.parentElement?.closest("details") as HTMLDetailsElement | null;
    }
    openParentFolds(target);
    const doScroll = () => {
      const fresh = root.querySelector<HTMLElement>(`#${CSS.escape(id)}`) || target;
      const beforeY = window.scrollY;
      const top = fresh.getBoundingClientRect().top + window.scrollY;
      window.scrollTo({ top, behavior: "smooth" });
      // Update URL hash without relying on default anchor behavior.
      if (window.location.hash !== `#${id}`) window.location.hash = `#${id}`;
      // Ensure active highlight matches the new scroll position.
      recompute();
      update_progress();
      // Fallback: if scroll didn't move, force a hash jump and retry.
      setTimeout(() => {
        if (Math.abs(window.scrollY - beforeY) < 2) {
          history.replaceState(null, "", window.location.pathname + window.location.search);
          window.location.hash = `#${id}`;
          fresh.scrollIntoView({ block: "start", inline: "nearest" });
        }
      }, 60);
    };
    // If we had to open folds, wait an extra frame so layout settles.
    if (firstClosed) {
      requestAnimationFrame(() => requestAnimationFrame(doScroll));
    } else {
      requestAnimationFrame(doScroll);
    }
  }

  function sanitizeHeadingLabel(text: string) {
    let out = text || '';
    // Collapse inline math: $...$ -> ...
    out = out.replace(/\$([^$]+)\$/g, (_m, inner) => inner);
    // Strip remaining math delimiters
    out = out.replace(/\$\$/g, '');
    // Simplify common LaTeX macros for readability
    out = out.replace(/\\text\{([^}]+)\}/g, '$1');
    out = out.replace(/\\mathrm\{([^}]+)\}/g, '$1');
    out = out.replace(/\\mathbf\{([^}]+)\}/g, '$1');
    out = out.replace(/\\mathit\{([^}]+)\}/g, '$1');
    out = out.replace(/\\mathcal\{([^}]+)\}/g, '$1');
    // Simplify subscripts/superscripts with braces: _{x} -> _x, ^{x} -> ^x
    out = out.replace(/_\{([^}]+)\}/g, '_$1');
    out = out.replace(/\^\{([^}]+)\}/g, '^$1');
    // Remove remaining backslashes used for LaTeX commands
    out = out.replace(/\\/g, '');
    // Normalize whitespace
    out = out.replace(/\s+/g, ' ').trim();
    return out;
  }

  function recompute() {
    if (!browser) return;
    container_el = document.querySelector(containerSelector) as HTMLElement | null;

    const nodes = container_el
      ? container_el.querySelectorAll(headingsSelector)
      : document.querySelectorAll(headingsSelector);

    headings = Array.from(nodes)
      .filter((el) => should_include_heading(el as HTMLElement))
      .map((el) => {
        const h = el as HTMLElement;
        if (!h.id) {
          // Fallback: generate a readable id from text content
          h.id = (h.textContent || '')
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
        }
        const inSummary = !!h.closest("summary");
        const d = h.closest("details") as HTMLDetailsElement | null;
        const inClosedDetails = !!(d && !d.open);
        const labelText = sanitizeHeadingLabel(h.textContent || '');
        const labelHtml = h.innerHTML || labelText;
        return {
          id: h.id,
          level: h.tagName === 'H2' ? 2 : 3,
          top: effectiveTopForHeading(h),
          labelText,
          labelHtml,
          inSummary,
          inClosedDetails,
          el: h,
        };
      });

    visibleHeadings = headings;
    updateVisibility();
    updateLabelWidth();
    update_progress();
  }

  function updateVisibility() {
    if (!browser) return;
    if (!container_el) {
      hideToc = false;
      return;
    }
    const root = document.documentElement;
    const vw = root?.clientWidth || window.innerWidth || 0;
    const hasHScroll = canHorizontallyScrollPage();

    // Hide if: (no horizontal scroll AND main text occupies "too much" of viewport).
    // Add hysteresis to prevent flicker when layout fluctuates near the threshold.
    // Tweak: keep TOC visible under more zoom by hiding only when the main column
    // is a larger fraction of the viewport.
    const RATIO_HIDE = 0.615;
    const RATIO_SHOW = 0.61; // must be < RATIO_HIDE

    if (hasHScroll || vw <= 0) {
      hideByWidth = false;
    } else {
      const MAIN_MAX_PX = 760; // keep in sync with app.css .layout-md
      // Important: use the intended main-column width (not measured width) to avoid
      // a feedback loop where hiding side cols changes the measured width, causing
      // flicker during zoom.
      const ratio = MAIN_MAX_PX / vw;

      if (!hideByWidth) {
        if (ratio >= RATIO_HIDE) hideByWidth = true;
      } else if (ratio <= RATIO_SHOW) {
        hideByWidth = false;
      }
    }

    hideToc = hideByWidth;

    // Publish a single source of truth for "side columns on/off" so footnotes can
    // bind to the TOC visibility.
    publishSideCols(hideToc ? "off" : "on");
  }

  function update_progress() {
    if (!browser) return;
    const y = window.scrollY + 8;
    let ans = -1;
    // Recompute top on the fly; folds/images can shift layout after recompute().
    for (let i = 0; i < headings.length; i += 1) {
      const h = headings[i];
      h.top = effectiveTopForHeading(h.el);
      if (h.top <= y) ans = i;
    }
    if (ans >= 0) {
      const top = headings[ans].top;
      if (headings[ans].inClosedDetails) {
        for (let i = ans; i >= 0 && headings[i].top === top; i -= 1) {
          if (headings[i].inSummary) {
            ans = i;
            break;
          }
        }
      }
    }
    active_index = ans;
    const allFolded = areAllH2SectionsFolded();
    showAll = isHovering || active_index < 0 || allFolded;
    visibleIdSet = showAll ? null : computeVisibleIdSet(active_index);
  }

  function computeVisibleIdSet(activeIdx: number) {
    if (activeIdx < 0) return null;
    let h2Idx = -1;
    for (let i = activeIdx; i >= 0; i -= 1) {
      if (headings[i].level === 2) {
        h2Idx = i;
        break;
      }
    }
    if (h2Idx < 0) return null;
    let end = headings.length;
    for (let i = h2Idx + 1; i < headings.length; i += 1) {
      if (headings[i].level === 2) {
        end = i;
        break;
      }
    }
    const ids = new Set<string>();
    for (let i = h2Idx; i < end; i += 1) {
      ids.add(headings[i].id);
    }
    return ids;
  }

  function areAllH2SectionsFolded() {
    if (!container_el) return false;
    const folds = Array.from(
      container_el.querySelectorAll<HTMLDetailsElement>("details[data-h2fold]"),
    );
    if (!folds.length) return false;
    return folds.every((d) => !d.open);
  }

  function schedule_progress() {
    if (!browser) return;
    if (scrollRaf !== null) return;
    scrollRaf = requestAnimationFrame(() => {
      scrollRaf = null;
      update_progress();
      updateTocLeftOnly();
    });
  }

  // list layout uses natural flow; no per-item positioning needed

  function updateLabelWidth() {
    if (!meterEl) return;
    if (!container_el) return;
    const rect = container_el.getBoundingClientRect();
    const leftMargin = Math.max(rect.left, 0);
    const gapVar = getComputedStyle(document.documentElement).getPropertyValue("--toc-gap")
      || getComputedStyle(document.documentElement).getPropertyValue("--side-gap");
    const gap = Math.max(0, Math.round(parseFloat(gapVar || "32") || 32)); // px between toc and main text
    const minLeftVar =
      getComputedStyle(document.documentElement).getPropertyValue("--toc-min-left");
    const minLeft = Math.max(0, Math.round(parseFloat(minLeftVar || "16") || 16));

    const items = meterEl.querySelectorAll<HTMLAnchorElement>(".toc-item:not(.hidden)");
    let contentWidth = 0;
    items.forEach((item) => {
      // Measure the "natural" (unwrapped) label width; `getBoundingClientRect().width`
      // is unreliable here because `.toc-item` is styled as `width: 100%` to keep a
      // consistent clickable area, and zoom/resizes can otherwise lock us into the
      // previous constrained width.
      const prevWidth = item.style.width;
      const prevWS = item.style.whiteSpace;
      item.style.width = "max-content";
      item.style.whiteSpace = "nowrap";
      const w = Math.ceil(item.getBoundingClientRect().width);
      item.style.width = prevWidth;
      item.style.whiteSpace = prevWS;
      contentWidth = Math.max(contentWidth, w);
    });
    if (contentWidth === 0) return;

    const available = Math.max(0, Math.floor(leftMargin - gap));
    const capVar = getComputedStyle(document.documentElement).getPropertyValue("--toc-max-width-cap");
    const cap = Math.max(0, Math.round(parseFloat(capVar || "320") || 320));
    const maxWidth = available > 0 ? Math.min(contentWidth, available) : contentWidth;
    meterEl.style.setProperty("--toc-max-width", `${Math.min(maxWidth, cap)}px`);

    // Keep TOC pinned to the left edge (no "hugging" movement).
    meterEl.style.setProperty("--toc-left", `${minLeft}px`);

    // Cache for scroll-time updates.
    lastTocWidth = Math.min(maxWidth, cap);
    lastTocGap = gap;
    lastTocMinLeft = minLeft;

    // Dynamically shrink the main column under zoom / tight viewports so it never
    // needs to slide under the fixed-left TOC.
    // Reserve: tocLeft + tocWidth + gap + a small safety gutter.
    const vw = document.documentElement.clientWidth || window.innerWidth || 0;
    const reserveLeft = minLeft + lastTocWidth + gap + 12;
    const baseMain = 760; // desired max width (keep in sync with app.css/layout-md)
    const computed = vw > 0 ? Math.min(baseMain, Math.max(520, vw - reserveLeft)) : baseMain;
    publishMainColWidthPx(computed);
  }

  function updateTocLeftOnly() {
    // No-op-ish now that TOC is pinned left; keep just in case vars change.
    if (!meterEl || !container_el) return;
    meterEl.style.setProperty("--toc-left", `${lastTocMinLeft}px`);
  }

  let onScroll: () => void;
  let onResize: () => void;
  let onToggle: (e: Event) => void;
  let ro: ResizeObserver | null = null;
  let meterEl: HTMLElement | null = null;
  let containerRoot: HTMLElement | null = null;

  onMount(() => {
    hydrated = true;
    syncTocMaxWidthCap();
    raf_id = requestAnimationFrame(() => {
      recompute();
      update_progress();
      ready = true;
    });
    onScroll = () => schedule_progress();
    onResize = () => recompute();
    onToggle = () => {
      // Fold/unfold changes heading positions; refresh measurements.
      recompute();
    };

    if (browser) {
      window.addEventListener('scroll', onScroll, { passive: true });
      window.addEventListener('resize', onResize);

      if (containerSelector) {
        const c = document.querySelector(containerSelector) as HTMLElement | null;
        if (c) {
          containerRoot = c;
          ro = new ResizeObserver(() => recompute());
          ro.observe(c);
          c.addEventListener("toggle", onToggle, true);
        }
      }

      // Initialize label width once layout is ready
      setTimeout(() => {
        updateVisibility();
        updateLabelWidth();
      }, 100);
      requestAnimationFrame(() => updateVisibility());

      // Zoom changes (browser zoom) do not reliably trigger resize events, so we
      // watch viewport width and refresh TOC visibility + placement when it changes.
      watchTimer = window.setInterval(() => {
        const root = document.documentElement;
        const vw = root?.clientWidth || window.innerWidth || 0;
        const dpr = window.devicePixelRatio || 1;
        if (vw === lastWatchVw && dpr === lastWatchDpr) return;
        lastWatchVw = vw;
        lastWatchDpr = dpr;
        updateVisibility();
        updateLabelWidth();
      }, 500);
    }
  });

  $: if (browser) {
    syncTocMaxWidthCap();
  }

  onDestroy(() => {
    if (browser) {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
    }
    if (browser && watchTimer !== null) {
      window.clearInterval(watchTimer);
      watchTimer = null;
    }
    if (browser) {
      const root = document.documentElement;
      if (root?.dataset?.[SIDE_DATASET_KEY]) delete root.dataset[SIDE_DATASET_KEY];
      lastPublishedSide = null;
      window.dispatchEvent(new CustomEvent("sidecolschange", { detail: { side: "on" } }));
    }
    if (ro) ro.disconnect();
    if (containerRoot && onToggle) {
      containerRoot.removeEventListener("toggle", onToggle, true);
    }
    if (raf_id) cancelAnimationFrame(raf_id);
    if (scrollRaf !== null) cancelAnimationFrame(scrollRaf);
  });
</script>

<!--
  Fixed, full-height bar on the extreme left (fills viewport regardless of layout).
  The gradient is fixed over the full bar; we reveal it via clip-path based on `progress`.
  Ticks are horizontal lines that start at the very left edge and extend into the page,
  and on hover they show the heading label to the right.
-->
<nav
  class="toc"
  bind:this={meterEl}
  aria-hidden="true"
  class:ready={ready}
  class:hidden={hideToc}
  on:wheel={onTocWheel}
  on:mouseenter={() => {
    isHovering = true;
    update_progress();
  }}
  on:mouseleave={() => {
    isHovering = false;
    update_progress();
  }}
>
  {#if hydrated}
    {#each visibleHeadings as h, i}
      <a
        href={`#${h.id}`}
        class={`toc-item ${h.level === 3 ? 'sub' : ''} ${i === active_index ? 'active' : ''} ${!showAll && visibleIdSet && !visibleIdSet.has(h.id) ? 'hidden' : ''}`}
        title={h.labelText}
        on:click|preventDefault={() => gotoHeading(h.id)}
      >
        {@html h.labelHtml}
      </a>
    {/each}
  {/if}
</nav>

<style>
  :root {
    --toc-max-width: 280px;
    --toc-left: 28px;
    --toc-max-width-cap: 220px;
  }

  .toc {
    position: fixed;
    left: var(--toc-left, 28px);
    top: 24px;
    bottom: 24px;
    transform: none;
    width: var(--toc-max-width, 280px);
    height: auto;
    max-height: none;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding-right: 0;
    z-index: 50;
    opacity: 0;
    transition: opacity 400ms ease;
    text-align: left;
  }

  .toc.ready {
    opacity: 1;
  }

  .toc.hidden {
    display: none;
  }

  .toc-item.hidden {
    visibility: hidden;
    pointer-events: none;
  }

  .toc-item {
    display: block;
    width: 100%;
    text-align: left;
    overflow-wrap: anywhere;
    word-break: break-word;
    color: #6b7280;
    font-size: 13px;
    line-height: 1.6;
    text-decoration: none;
    margin: 6px 0; /* fixed spacing between all items */
  }

  .toc-item:hover {
    color: #111827;
  }

  .toc-item.active {
    color: #111827;
    font-weight: 600;
  }


  .toc-item.sub {
    padding-left: 14px;
    color: #9ca3af;
    font-size: 13px;
  }

  /* No collapsing/hiding of items; TOC always shows all headings. */

  /* Do NOT hide the TOC via media queries; visibility is controlled by `hideToc`
     so we can keep TOC and footnotes bound to the same state. */
</style>
