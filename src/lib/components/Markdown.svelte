<script context="module" lang="ts">
  import { marked } from "marked";
  import katex from "katex";
  import "katex/dist/katex.min.css";
  import { base } from "$app/paths";

  // The site is served under a base path (e.g. /RIME on GitHub Pages).
  // Root-absolute URLs written in the post ("/assets/x.png") are prefixed with
  // it; relative URLs ("assets/x.png") already resolve against the page URL.
  // `base` is read at call time on purpose: during prerendering SvelteKit sets
  // it to a relative path, in the browser it is the absolute prefix.
  function withBase(url: string) {
    return /^\/(?!\/)/.test(url) ? `${base}${url}` : url;
  }

  // Same rewrite for raw HTML in the post (<img src>, <iframe src>, <a href>, ...).
  function rewriteRootUrls(html: string) {
    return html.replace(
      /(\s(?:src|href|poster|data)\s*=\s*["'])\/(?!\/)/gi,
      (_m, pre) => `${pre}${base}/`,
    );
  }

  function normalizeFootnoteId(id: string) {
    // Keep in sync with the renderer/link ids; allow common id chars like '-' and '_'.
    return String(id).replace(/[^a-zA-Z0-9\-_]/g, "");
  }

  function renderMath(tex: string, displayMode: boolean) {
    try {
      return katex.renderToString(tex, { throwOnError: false, displayMode });
    } catch {
      const tag = displayMode ? "pre" : "code";
      return `<${tag} class="katex-error">${tex}</${tag}>`;
    }
  }

  const mathBlock = {
    name: "mathBlock",
    level: "block",
    start: (src: string) => src.match(/\$\$/)?.index,
    tokenizer(src: string) {
      const match = /^\$\$([\s\S]+?)\$\$/.exec(src);
      if (match)
        return { type: "mathBlock", raw: match[0], text: match[1].trim() };
    },
    renderer: (token: any) =>
      `<div class="math math-block">${renderMath(token.text, true)}</div>`,
  };

  const mathInline = {
    name: "mathInline",
    level: "inline",
    start: (src: string) => src.match(/\$/)?.index,
    tokenizer(src: string) {
      const match = /^\$([^\$\n]+?)\$/.exec(src);
      if (match)
        return { type: "mathInline", raw: match[0], text: match[1].trim() };
    },
    renderer: (token: any) =>
      `<span class="math math-inline">${renderMath(token.text, false)}</span>`,
  };

  // Notion color text extension: ::color[text]::
  const colorText = {
    name: "colorText",
    level: "inline",
    start: (src: string) => src.match(/::/)?.index,
    tokenizer(src: string) {
      const match = /^::(gray|brown|orange|yellow|green|blue|purple|pink|red)\[([^\]]+?)\]::/.exec(src);
      if (match) {
        return { 
          type: "colorText", 
          raw: match[0], 
          color: match[1],
          text: match[2]
        };
      }
    },
    renderer: (token: any) => {
      // Notion's default text colors
      const colors: Record<string, string> = {
        gray: "#9B9A97",
        brown: "#64473A",
        orange: "#D9730D",
        yellow: "#DFAB01",
        green: "#0F7B6C",
        blue: "#0B6E99",
        purple: "#6940A5",
        pink: "#AD1A72",
        red: "#E03E3D",
      };
      const color = colors[token.color] || colors.gray;
      // Parse inner Markdown (bold, italic, etc.)
      const innerHtml = marked.parseInline(token.text);
      return `<span style="color: ${color};">${innerHtml}</span>`;
    },
  };

  const customRenderer = {
    link(href: string, title: string | null, text: string) {
      const isInternal = /^(\/|#|[A-Za-z0-9\-_]+(\.html?)?$)/.test(href);
      let out = `<a href="${encodeURI(withBase(href))}" class="link"`;
      if (!isInternal)
        out += ` target="_blank" rel="external noopener noreferrer"`;
      if (title) out += ` title="${title}"`;
      out += `>${text}</a>`;
      return out;
    },
    html(html: string) {
      return rewriteRootUrls(html);
    },
    paragraph(text: string) {
      // Notion cannot caption tables, so table captions are written as a grey paragraph
      // ("::gray[*Table N.* ...]::") below the table. Render them like figure captions.
      const m = /^<span style="color: #9B9A97;">(<em>Table (\d+)\.<\/em>[\s\S]*)<\/span>$/.exec(text.trim());
      if (m) {
        return `<div class='md-figcaption md-tablecaption text-left text-gray-500 mb-4 text-sm' data-table-num="${m[2]}"><p>${m[1]}</p></div>\n`;
      }
      return `<p>${text}</p>\n`;
    },
    heading(text: string, level: number, raw: string, slugger: any) {
      const id = slugger ? slugger.slug(raw) : slugify(raw || text);
      // Keep plain heading text; the scroll meter will link to #id
      return `<h${level} id="${id}">${text}</h${level}>`;
    },
    blockquote(quote: string) {
      return `<blockquote class="inline-block bg-neutral-50 border-l-4 border-neutral-600 rounded px-3 py-2 align-middle my-2">${quote}</blockquote>`;
    },
    image(href: string, title: string | null, text: string) {
      // Don't render images with placeholder or empty src (avoid 404s)
      if (!href || href === '__IMAGE_PLACEHOLDER__' || href.trim() === '') {
        if (text) {
          // Render caption only if alt text exists
          return `<div class="text-left text-gray-400 italic text-sm my-4">[Image: ${text}]</div>`;
        }
        return '<!-- image placeholder -->';
      }
      // Normal image rendering
      const id = text ? `fig-${slugify(text)}` : "";
      let out = `<img src="${withBase(href)}" alt="${text || ''}" ${id ? `id="${id}" ` : ""}class="block mx-auto unselectable" />`;

      // Render caption from image title (match imageAttrExtension behavior)
      if (title) {
        const m = /\bFigure\s+(\d+)\b/i.exec(String(title || ""));
        const figNumAttr = m ? ` data-fig-num="${m[1]}"` : "";
        const cap = boldFigurePrefix(String(title || ""));
        out += `<div class='md-figcaption text-left text-gray-500 mb-4 md:px-8 lg:px-12 text-sm'${figNumAttr}>${marked.parse(cap)}</div>`;
      }
      return out;
    },
  };

  function boldFigurePrefix(rawTitle: string) {
    const s = String(rawTitle || "").trim();
    // Avoid double-bold if already styled.
    if (/^(?:\*\*|<strong>|\s*<b>)/i.test(s)) return s;
    // Bold leading "Figure 12:", "Figure 12.", "Figure 12(a):", etc.
    return s.replace(
      /^(Figure\s+\d+(?:\([a-z]\))?\s*(?:[:.]))(\s*)/i,
      "**$1**$2",
    );
  }

  function slugify(s: string) {
    return String(s || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  const imageAttrExtension = {
    name: "imageAttr",
    level: "inline",
    start: (src: string) => src.indexOf("!["),
    tokenizer(src: string) {
      const re = /^!\[([^\]]*)\]\((\S+?)(?:\s+"([^"]*)")?\)\{([^}]+)\}/;
      const match = re.exec(src);
      if (match) {
        const [raw, alt, srcUrl, title, attrStr] = match;
        const attrs: Record<string, string> = {};
        attrStr.split(/\s+/).forEach((tok) => {
          if (!tok) return;
          const eq = tok.indexOf("=");
          if (eq === -1) {
            attrs[tok] = "";
          } else {
            const k = tok.slice(0, eq);
            const v = tok.slice(eq + 1).replace(/^["']|["']$/g, "");
            if (k) attrs[k] = v;
          }
        });
        return { type: "imageAttr", raw, alt, src: srcUrl, title, attrs };
      }
    },
    renderer(token: any) {
      const isVideoSrc = /\.(mp4|webm|ogg)(\?.*)?$/i.test(token.src);
      const declaresVideo =
        token.attrs["type"] === "video" ||
        Object.prototype.hasOwnProperty.call(token.attrs, "video");
      let out = "";
      if (isVideoSrc || declaresVideo) {
        const lower = token.src.toLowerCase();
        const sourceType =
          token.attrs["source-type"] ||
          (lower.endsWith(".webm")
            ? "video/webm"
            : lower.endsWith(".ogg")
              ? "video/ogg"
              : "video/mp4");

        // read optional freeze ms from markdown: {... freeze=10000}
        const freezeMs = token.attrs["freeze"] || "10000";

        const figId = token.attrs["id"] || `fig-${slugify(token.alt || "")}`;
        out += `<video class="block mx-auto autoplay-on-fullview md-video unselectable" aria-label="${token.alt || ""}" id="${figId}"`;
        const hasPlaysinline = Object.prototype.hasOwnProperty.call(
          token.attrs,
          "playsinline",
        );

        // forward arbitrary attrs except type/video/source-type/freeze/controls
        for (const k in token.attrs) {
          if (
            k === "type" ||
            k === "video" ||
            k === "source-type" ||
            k === "freeze" ||
            k === "controls" ||
            k === "id"
          )
            continue;
          const val = token.attrs[k];
          out += val === "" ? ` ${k}` : ` ${k}="${val}"`;
        }

        // autoplay reliability
        out += " muted playsinline"; // keep muted for autoplay; playsinline for iOS
        if (!hasPlaysinline) out += " playsinline";

        // carry freeze config for runtime
        out += ` data-freeze-ms="${freezeMs}"`;

        out += `><source src="${withBase(token.src)}#t=0.1" type="${sourceType}" /></video>`;
      } else {
        const figId = token.attrs["id"] || `fig-${slugify(token.alt)}`;
        out += `<img src="${withBase(token.src)}" alt="${token.alt}" id="${figId}" class="block mx-auto unselectable"`;
        for (const k in token.attrs) {
          if (k === "id") continue;
          out += ` ${k}="${token.attrs[k]}"`;
        }
        out += " />";
      }
      if (token.title) {
        const m = /\bFigure\s+(\d+)\b/i.exec(String(token.title || ""));
        const figNumAttr = m ? ` data-fig-num="${m[1]}"` : "";
        const cap = boldFigurePrefix(String(token.title || ""));
        out += `<div class='md-figcaption text-left text-gray-500 mb-4 md:px-8 lg:px-12 text-sm'${figNumAttr}>${marked.parse(cap)}</div>`;
      }
      return out;
    },
  };

  marked.use({
    gfm: true,
    extensions: [imageAttrExtension, mathBlock, mathInline, colorText],
    // Positional renderer signatures are the marked <=12 API (marked 13 switched
    // to token objects), so keep marked pinned to 12.x.
    renderer: customRenderer as any,
  });
</script>

<script lang="ts">
  import Jumpbox from "./Jumpbox.svelte";
  import CalloutBox from "./CalloutBox.svelte";
  import FoldBox from "./FoldBox.svelte";

  export let source: string;

  type Footnote = { id: string; safeId: string; num: number; html: string };

  type Chunk =
    | { type: "text"; content: string }
    | { type: "jumpbox"; id: string; label?: string }
    | { type: "small"; content: string }
    | { type: "callout"; variant: "note" | "tip" | "warning" | "info" | "takeaway"; title: string; content: string }
    | { type: "fold"; title: string; open: boolean; content: string }
    | { type: "h2"; id: string; text: string }
    | { type: "h3"; id: string; text: string };

  type RenderChunk = Exclude<Chunk, { type: "h2"; id: string; text: string }>;

  type H3SectionItem =
    | { type: "chunk"; chunk: RenderChunk }
    | {
        type: "subsection";
        heading: { id: string; text: string; html: string };
        children: RenderChunk[];
      };

  type SectionItem =
    | { type: "chunk"; chunk: RenderChunk }
    | {
        type: "section";
        heading: { id: string; text: string; html: string };
        children: RenderChunk[];
      };

  // Regexes (global + multiline). We scan by hand using lastIndex.
  const JUMP_RE = /:::jumpbox\s+id="([^"]+)"(?:\s+label="([^"]+)")?\s*:::/gm;
  const TAKE_BEGIN_RE = /:::takeaway_begin:::/gm;
  const TAKE_END_RE = /:::takeaway_end:::/gm;
  const SMALL_BEGIN_RE = /:::small_begin:::/gm;
  const SMALL_END_RE = /:::small_end:::/gm;
  const CALLOUT_BEGIN_RE =
    /:::callout_begin(?:\s+type="([^"]+)")?(?:\s+title="([^"]+)")?\s*:::/gm;
  const CALLOUT_END_RE = /:::callout_end:::/gm;
  const FOLD_BEGIN_RE =
    /:::fold_begin(?:\s+title="([^"]+)")?(?:\s+(open))?\s*:::/gm;
  const FOLD_END_RE = /:::fold_end:::/gm;
  const H2_RE = /^##(?!#)\s+(.+?)\s*$/gm;
  const H3_RE = /^###(?!#)\s+(.+?)\s*$/gm;

  function createSlugger() {
    const seen = new Map<string, number>();
    return {
      slug(raw: string) {
        const base = slugify(raw || "") || "section";
        const prev = seen.get(base) ?? 0;
        seen.set(base, prev + 1);
        return prev === 0 ? base : `${base}-${prev}`;
      },
    };
  }

  function extractFootnotes(md: string) {
    const lines = md.split("\n");
    const mainLines: string[] = [];
    const footnotes: { id: string; safeId: string; raw: string[] }[] = [];
    let current: { id: string; safeId: string; raw: string[] } | null = null;

    for (const line of lines) {
      const match = line.match(/^\[\^([^\]]+)\]:\s*(.*)$/);
      if (match) {
        if (current) footnotes.push(current);
        const id = match[1];
        current = { id, safeId: normalizeFootnoteId(id), raw: [match[2]] };
        continue;
      }

      if (current) {
        if (/^\s{2,}|\t/.test(line)) {
          current.raw.push(line.replace(/^\s+/, ""));
          continue;
        }
        footnotes.push(current);
        current = null;
      }

      mainLines.push(line);
    }

    if (current) footnotes.push(current);

    const cleaned = mainLines.join("\n");
    const notes = footnotes.map((fn) => ({
      id: fn.id,
      safeId: fn.safeId,
      html: marked.parse(restoreCode(fn.raw.join("\n"))) as string,
    }));

    return { main: cleaned, notes };
  }

  function computeFootnoteNumbering(main: string, notes: { id: string; safeId: string; html: string }[]) {
    // Number by first appearance in the main text.
    const order: string[] = [];
    const seen = new Set<string>();
    const re = /\[\^([^\]]+)\]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(main)) !== null) {
      const safeId = normalizeFootnoteId(m[1]);
      if (!safeId || seen.has(safeId)) continue;
      seen.add(safeId);
      order.push(safeId);
    }

    const noteBySafeId = new Map(notes.map((n) => [n.safeId, n]));
    const numbered: Footnote[] = [];
    const idToNum = new Map<string, number>();
    let next = 1;

    for (const safeId of order) {
      const n = noteBySafeId.get(safeId);
      if (!n) continue;
      idToNum.set(safeId, next);
      numbered.push({ ...n, num: next });
      next += 1;
    }

    // Append any defined-but-unreferenced notes at the end (rare, but keep deterministic).
    for (const n of notes) {
      if (idToNum.has(n.safeId)) continue;
      idToNum.set(n.safeId, next);
      numbered.push({ ...n, num: next });
      next += 1;
    }

    return { idToNum, numbered };
  }

  function replaceFootnoteRefs(md: string, idToNum: Map<string, number>) {
    return md.replace(/\[\^([^\]]+)\]/g, (_m, id) => {
      const safeId = normalizeFootnoteId(id);
      const num = idToNum.get(safeId);
      const label = num ? String(num) : String(id);
      return `<sup class="footnote-ref"><a href="#fn-${safeId}" data-fn="${safeId}">${label}</a></sup>`;
    });
  }

  // --- Code protection -------------------------------------------------------
  // Block markers (:::fold_begin::: ...), the ##/### section split and [^id]
  // footnotes are found with regexes over the raw source. Fenced code blocks
  // and single-line inline code spans are swapped for opaque placeholders first,
  // so a "## comment" line inside a code block, a regex like `[^a-z]`, or a
  // marker shown as an example in code is left alone. Placeholders are restored
  // right before Markdown parsing (toHtml, headings, titles, footnotes).
  const CODE_OPEN = "\uE000";
  const CODE_CLOSE = "\uE001";
  const CODE_PLACEHOLDER_RE = /\uE000(\d+)\uE001/g;
  let codeSegments: string[] = [];

  function protectCode(md: string) {
    const segs: string[] = [];
    const stash = (m: string) => {
      segs.push(m);
      return `${CODE_OPEN}${segs.length - 1}${CODE_CLOSE}`;
    };
    // Fenced blocks (``` or ~~~, up to 3 spaces of indent), closed by the same
    // fence or by the end of the document.
    let out = md.replace(
      /^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?(?:^ {0,3}\1[`~]*[ \t]*$|(?![\s\S]))/gm,
      stash,
    );
    // Inline code spans (single line; any backtick-run length).
    out = out.replace(/(`+)(?!`)([^\n]*?[^`\n])\1(?!`)/g, stash);
    return { text: out, segs };
  }

  function restoreCode(md: string) {
    return md.replace(CODE_PLACEHOLDER_RE, (_m, i) => codeSegments[Number(i)] ?? "");
  }

  let processedSource = source;
  let footnotes: Footnote[] = [];
  const htmlCache = new Map<string, string>();

  $: {
    const protectedSource = protectCode(source || "");
    codeSegments = protectedSource.segs;
    const { main, notes } = extractFootnotes(protectedSource.text);
    const { idToNum, numbered } = computeFootnoteNumbering(main, notes);
    processedSource = replaceFootnoteRefs(main, idToNum);
    footnotes = numbered;
    // Best-effort: avoid unbounded growth. Source changes are rare; clear on change.
    htmlCache.clear();
  }

  function toHtml(md: string) {
    const key = md || "";
    const cached = htmlCache.get(key);
    if (cached !== undefined) return cached;
    const html = marked.parse(restoreCode(key)) as string;
    htmlCache.set(key, html);
    return html;
  }

  // One-pass tokenizer across the whole document
  $: chunks = (() => {
    const out: Chunk[] = [];
    let pos = 0;
    const slugger = createSlugger();
    const doc = processedSource || "";

    while (pos < doc.length) {
      // Find next possible jumpbox or takeaway-begin after pos
      JUMP_RE.lastIndex = pos;
      TAKE_BEGIN_RE.lastIndex = pos;
      SMALL_BEGIN_RE.lastIndex = pos;
      CALLOUT_BEGIN_RE.lastIndex = pos;
      FOLD_BEGIN_RE.lastIndex = pos;
      H2_RE.lastIndex = pos;
      H3_RE.lastIndex = pos;

      const j = JUMP_RE.exec(doc);
      const t = TAKE_BEGIN_RE.exec(doc);
      const s = SMALL_BEGIN_RE.exec(doc);
      const c = CALLOUT_BEGIN_RE.exec(doc);
      const f = FOLD_BEGIN_RE.exec(doc);
      const h2 = H2_RE.exec(doc);
      const h3 = H3_RE.exec(doc);

      // No more markers → push rest as text and stop
      if (!j && !t && !s && !c && !f && !h2 && !h3) {
        if (pos < doc.length) out.push({ type: "text", content: doc.slice(pos) });
        break;
      }

      // Choose the earliest marker by index
      const j_idx = j ? j.index : Infinity;
      const t_idx = t ? t.index : Infinity;
      const s_idx = s ? s.index : Infinity;
      const c_idx = c ? c.index : Infinity;
      const f_idx = f ? f.index : Infinity;
      const h2_idx = h2 ? h2.index : Infinity;
      const h3_idx = h3 ? h3.index : Infinity;
      const min_idx = Math.min(j_idx, t_idx, s_idx, c_idx, f_idx, h2_idx, h3_idx);

      if (h2_idx === min_idx) {
        const begin_idx = h2!.index;
        const begin_end = begin_idx + h2![0].length;
        if (begin_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, begin_idx) });

        const text = restoreCode((h2![1] ?? "").trim());
        const id = slugger.slug(text);
        out.push({ type: "h2", id, text });

        pos = begin_end;
      } else if (h3_idx === min_idx) {
        const begin_idx = h3!.index;
        const begin_end = begin_idx + h3![0].length;
        if (begin_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, begin_idx) });

        const text = restoreCode((h3![1] ?? "").trim());
        const id = slugger.slug(text);
        out.push({ type: "h3", id, text });

        pos = begin_end;
      } else if (j_idx === min_idx) {
        // Emit pre-text
        if (j_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, j_idx) });

        const id = j![1];
        out.push({ type: "jumpbox", id, label: j![2] ? restoreCode(j![2]) : undefined });

        // Advance past this jumpbox
        pos = JUMP_RE.lastIndex;
      } else if (t_idx === min_idx) {
        // Takeaway begin comes first
        const begin_idx = t!.index;
        const begin_end = begin_idx + t![0].length;

        // Emit pre-text
        if (begin_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, begin_idx) });

        // Find matching end after the begin
        TAKE_END_RE.lastIndex = begin_end;
        const tend = TAKE_END_RE.exec(doc);

        if (!tend) {
          // No closing marker → treat the begin marker as plain text (no guessing)
          out.push({
            type: "text",
            content: doc.slice(begin_idx, begin_end),
          });
          pos = begin_end;
          continue;
        }

        const inner_md = doc.slice(begin_end, tend.index).trim();
        out.push({ type: "callout", variant: "takeaway", title: "", content: inner_md });

        // Advance past the end marker
        pos = TAKE_END_RE.lastIndex;
      } else if (s_idx === min_idx) {
        // Small begin comes first
        const begin_idx = s!.index;
        const begin_end = begin_idx + s![0].length;

        // Emit pre-text
        if (begin_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, begin_idx) });

        // Find matching end after the begin
        SMALL_END_RE.lastIndex = begin_end;
        const send = SMALL_END_RE.exec(doc);

        if (!send) {
          // No closing marker → treat the begin marker as plain text
          out.push({
            type: "text",
            content: doc.slice(begin_idx, begin_end),
          });
          pos = begin_end;
          continue;
        }

        const inner_md = doc.slice(begin_end, send.index).trim();
        out.push({ type: "small", content: inner_md });

        // Advance past the end marker
        pos = SMALL_END_RE.lastIndex;
      } else if (c_idx === min_idx) {
        // Callout block
        const begin_idx = c!.index;
        const begin_end = begin_idx + c![0].length;

        if (begin_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, begin_idx) });

        CALLOUT_END_RE.lastIndex = begin_end;
        const cend = CALLOUT_END_RE.exec(doc);
        if (!cend) {
          out.push({ type: "text", content: doc.slice(begin_idx, begin_end) });
          pos = begin_end;
          continue;
        }

        const variantRaw = (c![1] ?? "note").toLowerCase();
        const variant =
          (["note", "tip", "warning", "info", "takeaway"].includes(variantRaw)
            ? variantRaw
            : "note") as any;
        const title = restoreCode(c![2] ?? "");
        const inner_md = doc.slice(begin_end, cend.index).trim();
        out.push({ type: "callout", variant, title, content: inner_md });

        pos = CALLOUT_END_RE.lastIndex;
      } else {
        // Fold block
        const begin_idx = f!.index;
        const begin_end = begin_idx + f![0].length;

        if (begin_idx > pos)
          out.push({ type: "text", content: doc.slice(pos, begin_idx) });

        FOLD_END_RE.lastIndex = begin_end;
        const fend = FOLD_END_RE.exec(doc);
        if (!fend) {
          out.push({ type: "text", content: doc.slice(begin_idx, begin_end) });
          pos = begin_end;
          continue;
        }

        const title = restoreCode(f![1] ?? "Details");
        const open = !!f![2];
        const inner_md = doc.slice(begin_end, fend.index).trim();
        out.push({ type: "fold", title, open, content: inner_md });

        pos = FOLD_END_RE.lastIndex;
      }
    }

    return out;
  })();

  $: sections = (() => {
    const out: SectionItem[] = [];
    let current:
      | {
          heading: { id: string; text: string; html: string };
          children: RenderChunk[];
        }
      | null =
      null;

    for (const ch of chunks) {
      if (ch.type === "h2") {
        if (current) out.push({ type: "section", ...current });
        const inline = marked.parseInline(ch.text) as string;
        const h2Html = `<h2 id="${ch.id}">${inline}</h2>`;
        current = {
          heading: { id: ch.id, text: ch.text, html: h2Html },
          children: [],
        };
        continue;
      }

      const renderable = ch as RenderChunk;
      if (current) current.children.push(renderable);
      else out.push({ type: "chunk", chunk: renderable });
    }

    if (current) out.push({ type: "section", ...current });
    return out;
  })();

  function buildH3Sections(children: RenderChunk[]) {
    const out: H3SectionItem[] = [];
    let current:
      | {
          heading: { id: string; text: string; html: string };
          children: RenderChunk[];
        }
      | null = null;

    for (const ch of children) {
      if (isPinnedTakeaway(ch)) {
        if (current) out.push({ type: "subsection", ...current });
        current = null;
        out.push({ type: "chunk", chunk: ch });
        continue;
      }
      if (ch.type === "h3") {
        if (current) out.push({ type: "subsection", ...current });
        const inline = marked.parseInline(ch.text) as string;
        const h3Html = `<h3 id="${ch.id}">${inline}</h3>`;
        current = {
          heading: { id: ch.id, text: ch.text, html: h3Html },
          children: [],
        };
        continue;
      }

      const renderable = ch as RenderChunk;
      if (current) current.children.push(renderable);
      else out.push({ type: "chunk", chunk: renderable });
    }

    if (current) out.push({ type: "subsection", ...current });
    return out;
  }

  // Every ### section starts expanded (the original template only opened
  // headings starting with "Question N"). Readers can still collapse them; use
  // :::fold_begin::: for content that should start hidden.
  function shouldOpenH3(sub: H3SectionItem): boolean {
    return sub.type === "subsection";
  }

  function isPinnedTakeaway(chunk: RenderChunk): boolean {
    if (chunk.type !== "callout") return false;
    if (chunk.variant === "takeaway") return true;
    if ((chunk.title || "").toLowerCase().includes("takeaway")) return true;
    // Fallback: detect a bold "Takeaways" heading in the content body.
    const head = (chunk.content || "").slice(0, 200).toLowerCase();
    return /^\s*\*\*.*takeaway/.test(head);
  }

  import { onMount, afterUpdate, onDestroy } from "svelte";

  let container: HTMLDivElement | null = null;
  let footnoteAside: HTMLElement | null = null;
  let footnoteList: HTMLOListElement | null = null;
  let shellEl: HTMLDivElement | null = null;
  let sideMO: MutationObserver | null = null;
  // Side column visibility is controlled by the TOC (ScrollMeter) via
  // `document.documentElement.dataset.sidecols` + the `sidecolschange` event.

  let alignRaf: number | null = null;
  let alignRO: ResizeObserver | null = null;
  let sideRO: ResizeObserver | null = null;

  function scheduleAlign() {
    if (alignRaf !== null) return;
    alignRaf = requestAnimationFrame(() => {
      alignRaf = null;
      alignFootnotes();
    });
  }

  function updateSideVisibility() {
    if (!shellEl || !container || typeof window === "undefined") return;
    const root = document.documentElement;
    const sideFromToc = root?.dataset?.sidecols;
    if (sideFromToc === "on" || sideFromToc === "off") {
      if (shellEl.dataset.side !== sideFromToc) {
        shellEl.dataset.side = sideFromToc;
        scheduleAlign();
      }
      return;
    }
    // If the TOC hasn't published visibility yet, don't override the current state.
    // We'll sync on the next `sidecolschange` event / resize / update.
    return;
  }

  function alignFootnotes() {
    if (!container || !footnoteAside || !footnoteList) return;
    if (shellEl?.dataset.side === "off") {
      // Single-column layout (narrow viewport): there is no margin, so show
      // all notes as a plain numbered list after the article. (The original
      // template hid them entirely, so citations vanished on phones.)
      footnoteAside.querySelectorAll<HTMLLIElement>("li[id^='fn-']").forEach((li) => {
        li.style.display = "";
        li.style.position = "";
        li.style.top = "";
        li.style.marginTop = "";
      });
      footnoteList.style.minHeight = "";
      if (shellEl) shellEl.dataset.fnAligned = "1";
      return;
    }
    const isInClosedDetails = (el: Element) => {
      const d = el.closest("details") as HTMLDetailsElement | null;
      return !!(d && !d.open);
    };

    const refs = Array.from(
      container.querySelectorAll<HTMLAnchorElement>(".footnote-ref a[data-fn]"),
    ).filter((a) => !isInClosedDetails(a));
    if (!refs.length) return;

    const items = new Map<string, HTMLLIElement>();
    footnoteAside
      .querySelectorAll<HTMLLIElement>("li[id^='fn-']")
      .forEach((li) => items.set(li.id.replace(/^fn-/, ""), li));

    // Reset: hide everything, then re-show + position only notes that have visible refs.
    footnoteAside
      .querySelectorAll<HTMLLIElement>("li[id^='fn-']")
      .forEach((li) => {
        li.style.display = "none";
        li.style.position = "";
        li.style.top = "";
        li.style.marginTop = "";
      });

    const listRect = footnoteList.getBoundingClientRect();
    const footnoteStyles = getComputedStyle(footnoteAside);
    const fontSize = parseFloat(footnoteStyles.fontSize || "14");
    const lineHeightRaw = footnoteStyles.lineHeight;
    const lineHeight =
      lineHeightRaw === "normal"
        ? fontSize * 1.6
        : parseFloat(lineHeightRaw || String(fontSize * 1.6));
    const used = new Set<string>();

    // Collect desired positions first, then resolve overlaps (citations close together).
    const entries: { id: string; li: HTMLLIElement; desiredTop: number; height: number }[] =
      [];

    // Position each footnote at the same vertical line as its reference
    for (const ref of refs) {
      const id = ref.dataset.fn;
      if (!id || used.has(id)) continue;
      const li = items.get(id);
      if (!li) continue;
      used.add(id);
      li.style.display = "flex";

      // The ref is rendered as a <sup> (see renderer), so its own rect is *not*
      // representative of the containing text line. Use a collapsed Range to
      // obtain the actual line box at the ref position.
      const supEl = ref.closest("sup.footnote-ref") as HTMLElement | null;
      const anchorEl = supEl ?? ref;
      let lineRect: DOMRect | null = null;
      try {
        const range = document.createRange();
        range.setStartBefore(anchorEl);
        range.collapse(true);
        const rects = range.getClientRects();
        if (rects && rects.length) lineRect = rects[rects.length - 1] as DOMRect;
      } catch {
        // ignore; fallback below
      }
      if (!lineRect) lineRect = anchorEl.getBoundingClientRect();

      // `li` is absolutely positioned *inside* the <ol>, so convert viewport Y → <ol>-local Y.
      const lineMidY = lineRect.top + lineRect.height / 2;
      const desiredTop = lineMidY - lineHeight / 2 - listRect.top;

      // Stage for measurement; final placement happens after overlap resolution.
      li.style.position = "absolute";
      li.style.top = `0px`;
      li.style.marginTop = "0px";
      entries.push({ id, li, desiredTop, height: 0 });
    }

    if (entries.length) {
      // Measure heights after we've ensured absolute positioning.
      for (const e of entries) {
        e.height = e.li.getBoundingClientRect().height || lineHeight;
      }

      // Resolve overlaps by pushing down later notes.
      entries.sort((a, b) => a.desiredTop - b.desiredTop);
      const gapVar = getComputedStyle(document.documentElement).getPropertyValue(
        "--footnote-item-gap",
      );
      const gap = Math.max(0, Math.round(parseFloat(gapVar || "28") || 28)); // px between notes
      let prevBottom = -Infinity;
      for (const e of entries) {
        const top = Math.max(e.desiredTop, prevBottom + gap);
        e.li.style.top = `${Math.round(top)}px`;
        prevBottom = top + e.height;
      }

      // Ensure the <ol> is tall enough so pushed-down notes don't get clipped.
      const needed = Math.ceil(prevBottom + 12);
      const current = footnoteList.getBoundingClientRect().height;
      footnoteList.style.minHeight = `${Math.max(needed, Math.ceil(current))}px`;
    }

    // Mark as aligned to avoid initial "jump" while fonts/layout are settling.
    if (shellEl) shellEl.dataset.fnAligned = "1";
  }

  function setupVideos(root: HTMLElement) {
    const videos = Array.from(
      root.querySelectorAll<HTMLVideoElement>("video.autoplay-on-fullview"),
    );

    // De-dup if we re-run on updates
    const fresh = videos.filter((v) => !v.dataset._wired);

    if (fresh.length === 0) return;

    // Hover controls (desktop), keep hidden otherwise
    for (const v of fresh) {
      v.controls = false; // hidden by default
      v.dataset._wired = "1";

      let is_touch = false;
      const onFirstTouch = () => {
        is_touch = true;
        window.removeEventListener("touchstart", onFirstTouch);
      };
      window.addEventListener("touchstart", onFirstTouch, {
        passive: true,
        once: true,
      });

      const show = () => {
        if (!is_touch) v.controls = true;
      };
      const hide = () => {
        if (!is_touch) v.controls = false;
      };
      v.addEventListener("mouseenter", show);
      v.addEventListener("mouseleave", hide);
      v.addEventListener("focus", show);
      v.addEventListener("blur", hide);

      // Freeze at end → wait → restart
      let restart_timer: number | null = null;
      const clearTimer = () => {
        if (restart_timer !== null) {
          window.clearTimeout(restart_timer);
          restart_timer = null;
        }
      };

      const onEnded = () => {
        const freeze_ms = parseInt(v.dataset.freezeMs || "10000", 10);
        clearTimer();
        // Last frame remains visible when paused after 'ended'
        restart_timer = window.setTimeout(() => {
          try {
            v.currentTime = 0;
          } catch {}
          const p = v.play();
          if (p && typeof (p as any).catch === "function")
            (p as any).catch(() => {});
        }, freeze_ms);
      };

      const cancelers = ["play", "pause", "seeking", "emptied", "abort"].map(
        (evt) => v.addEventListener(evt, clearTimer),
      );
      v.addEventListener("ended", onEnded);

      // Store cleanup hooks
      (v as any)._cleanupVideo = () => {
        v.removeEventListener("mouseenter", show);
        v.removeEventListener("mouseleave", hide);
        v.removeEventListener("focus", show);
        v.removeEventListener("blur", hide);
        v.removeEventListener("ended", onEnded);
        clearTimer();
      };
    }

    // IntersectionObserver for full-visibility autoplay
    // Create once and stash it; reuse across updates.
    if (!(setupVideos as any)._io) {
      const io = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            const v = entry.target as HTMLVideoElement;
            // cancel pending restart if visibility changed
            const clear = (v as any)._clearRestartTimer as
              | (() => void)
              | undefined;
            if (clear) clear();

            if (entry.intersectionRatio >= 1.0) {
              const p = v.play();
              if (p && typeof (p as any).catch === "function")
                (p as any).catch(() => {});
            } else {
              v.pause();
            }
          }
        },
        { threshold: 1.0 },
      );

      (setupVideos as any)._io = io;
    }

    const io: IntersectionObserver = (setupVideos as any)._io;
    fresh.forEach((v) => io.observe(v));
  }

  function makeCodeBlocksCopyable(root: HTMLElement) {
    const blocks = Array.from(root.querySelectorAll('pre > code')) as HTMLElement[];

    for (const code of blocks) {
      const pre = code.parentElement as HTMLElement;
      if (!pre || pre.dataset.copyable) continue; // don’t duplicate

      pre.dataset.copyable = 'true';
      pre.style.position = 'relative';

      // Build button
      const button = document.createElement('button');
      button.textContent = 'Copy';
      button.className = 'copy-btn';
      button.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(code.innerText);
          button.textContent = 'Copied!';
          setTimeout(() => (button.textContent = 'Copy'), 1500);
        } catch {
          button.textContent = 'Error';
          setTimeout(() => (button.textContent = 'Copy'), 1500);
        }
      });

      pre.appendChild(button);
    }
  }

  function setupFigureRefLinks(root: HTMLElement) {
    if (typeof document === "undefined") return;

    // Build Figure number -> target id map from captions.
    const figNumToId = new Map<string, string>();
    const captions = Array.from(root.querySelectorAll<HTMLElement>(".md-figcaption[data-fig-num]"));
    for (const cap of captions) {
      const num = cap.dataset.figNum;
      if (!num) continue;
      const prev = cap.previousElementSibling as HTMLElement | null;
      const id = prev?.id;
      if (id) figNumToId.set(num, id);
    }
    if (!figNumToId.size) return;

    const shouldSkip = (el: Element | null) => {
      if (!el) return true;
      // Skip inside anchors / code blocks / captions themselves.
      return Boolean(el.closest("a, code, pre, script, style, .md-figcaption"));
    };

    // Linkify plain-text "Figure N" / "Fig N" / "Fig. N" in text nodes.
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node: Node) {
        const text = node.nodeValue || "";
        if (!text || !/\b(Figure|Fig\.?)\s+\d+\b/.test(text)) return NodeFilter.FILTER_REJECT;
        const parent = (node as Text).parentElement;
        if (shouldSkip(parent)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    } as any);

    const toProcess: Text[] = [];
    while (walker.nextNode()) toProcess.push(walker.currentNode as Text);

    const re = /\b(Figure|Fig\.?)\s+(\d+)\b/g;
    for (const node of toProcess) {
      const s = node.nodeValue || "";
      re.lastIndex = 0;
      let m: RegExpExecArray | null;
      let last = 0;
      const frag = document.createDocumentFragment();

      while ((m = re.exec(s)) !== null) {
        const match = m[0];
        const num = m[2];
        const targetId = figNumToId.get(num);
        if (!targetId) continue;

        if (m.index > last) frag.appendChild(document.createTextNode(s.slice(last, m.index)));
        const a = document.createElement("a");
        a.href = `#${targetId}`;
        a.className = "link figref";
        a.textContent = match;
        frag.appendChild(a);
        last = m.index + match.length;
      }

      if (last === 0) continue; // no replacements
      if (last < s.length) frag.appendChild(document.createTextNode(s.slice(last)));
      node.parentNode?.replaceChild(frag, node);
    }
  }

  // <iframe data-autoheight ...> (same-origin pages only, e.g. static/case-studies/)
  // is resized to its content height once loaded; the inline height is the
  // fallback and the size used before load.
  function setupAutoHeightIframes(root: HTMLElement) {
    root.querySelectorAll<HTMLIFrameElement>("iframe[data-autoheight]").forEach((f) => {
      if (f.dataset.autoheightWired) return;
      f.dataset.autoheightWired = "1";
      const fit = () => {
        try {
          const doc = f.contentDocument;
          if (!doc || doc.readyState !== "complete" || doc.URL === "about:blank") return;
          const h = Math.max(doc.documentElement.scrollHeight, doc.body?.scrollHeight ?? 0);
          if (h > 0) f.style.height = `${h + 2}px`;
        } catch {
          // Cross-origin: keep the declared height.
        }
      };
      f.addEventListener("load", fit);
      window.addEventListener("resize", fit, { passive: true });
      fit();
    });
  }

  function openFoldForCurrentHash() {
    if (typeof window === "undefined" || !container) return;
    const raw = window.location.hash || "";
    const id = raw.startsWith("#") ? raw.slice(1) : raw;
    if (!id) return;
    const target = container.querySelector<HTMLElement>(`#${CSS.escape(id)}`);
    if (!target) return;
    let d = target.closest("details.foldbox") as HTMLDetailsElement | null;
    while (d) {
      if (!d.open) d.open = true;
      d = d.parentElement?.closest("details.foldbox") as HTMLDetailsElement | null;
    }
  }

  onMount(() => {
    if (container) {
      // Respect default open/closed state set in the markup.
      openFoldForCurrentHash();
      setupVideos(container);
      makeCodeBlocksCopyable(container);
      setupFigureRefLinks(container);
      setupAutoHeightIframes(container);
      updateSideVisibility();
      scheduleAlign();
      // Recompute once after layout settles (grid, fonts, etc.)
      requestAnimationFrame(() => updateSideVisibility());
    }
    if (typeof window !== "undefined") {
      window.addEventListener("resize", scheduleAlign, { passive: true });
      window.addEventListener("resize", updateSideVisibility, { passive: true });
      window.addEventListener("hashchange", openFoldForCurrentHash as any, {
        passive: true,
      } as any);
      // Sync footnotes visibility to TOC visibility changes (dataset updates)
      // even when the change doesn't trigger a resize.
      window.addEventListener("sidecolschange", updateSideVisibility as any, {
        passive: true,
      } as any);

      // Extra safety: observe dataset changes directly, in case an event is missed.
      if ("MutationObserver" in window) {
        const root = document.documentElement;
        sideMO = new MutationObserver((mutations) => {
          for (const m of mutations) {
            if (m.type === "attributes" && m.attributeName === "data-sidecols") {
              updateSideVisibility();
              break;
            }
          }
        });
        sideMO.observe(root, { attributes: true, attributeFilter: ["data-sidecols"] });
      }
    }

    // Re-align when layout changes (fonts load, images settle, markdown reflows).
    if (typeof window !== "undefined" && "ResizeObserver" in window) {
      alignRO = new ResizeObserver(() => scheduleAlign());
      if (container) alignRO.observe(container);
      if (footnoteAside) alignRO.observe(footnoteAside);
    }
    if (typeof window !== "undefined" && "ResizeObserver" in window) {
      sideRO = new ResizeObserver(() => updateSideVisibility());
      if (container) sideRO.observe(container);
    }
    // Fonts loading often causes a delayed reflow without a resize event.
    const fonts = (document as any).fonts;
    if (fonts?.ready && typeof fonts.ready.then === "function") {
      fonts.ready.then(() => {
        updateSideVisibility();
        scheduleAlign();
      });
    }
  });

  afterUpdate(() => {
    if (container) {
      openFoldForCurrentHash();
      setupVideos(container); // handle markdown re-render
      makeCodeBlocksCopyable(container);
      setupFigureRefLinks(container);
      setupAutoHeightIframes(container);
      updateSideVisibility();
      scheduleAlign();
    }
  });

  onDestroy(() => {
    if (!(setupVideos as any)._io) return;
    const io: IntersectionObserver = (setupVideos as any)._io;
    if (!container) return;
    container.querySelectorAll("video.autoplay-on-fullview").forEach((v) => {
      io.unobserve(v);
      const cleanup = (v as any)._cleanupVideo;
      if (cleanup) cleanup();
    });
    if (typeof window !== "undefined") {
      window.removeEventListener("resize", scheduleAlign);
      window.removeEventListener("resize", updateSideVisibility);
      window.removeEventListener("sidecolschange", updateSideVisibility as any);
      window.removeEventListener("hashchange", openFoldForCurrentHash as any);
    }
    if (sideMO) {
      sideMO.disconnect();
      sideMO = null;
    }
    if (alignRO) alignRO.disconnect();
    if (sideRO) sideRO.disconnect();
  });
</script>

<div class="md-shell" bind:this={shellEl}>
  <div class="md-grid">
    <div class="md-output space-y-6" bind:this={container}>
      {#each sections as item, i (i)}
        {#if item.type === "chunk"}
          {#if item.chunk.type === "text"}
            <div class="md-output">{@html toHtml(item.chunk.content)}</div>
          {:else if item.chunk.type === "jumpbox"}
            <Jumpbox id={item.chunk.id} label={item.chunk.label} />
          {:else if item.chunk.type === "small"}
            <div class="md-output text-sm sm-block">{@html toHtml(item.chunk.content)}</div>
          {:else if item.chunk.type === "callout"}
            <CalloutBox
              variant={item.chunk.variant}
              title={item.chunk.title}
              html={toHtml(item.chunk.content)}
            />
          {:else if item.chunk.type === "fold"}
            <FoldBox title={item.chunk.title} open={item.chunk.open} html={toHtml(item.chunk.content)} />
          {/if}
        {:else if item.type === "section"}
          <details class="foldbox foldbox--h2" data-h2fold="1" open>
            <summary
              class="foldbox__summary foldbox__summary--h2"
              on:click={(e) => {
                if (typeof window === "undefined") return;
                const details = e.currentTarget.parentElement;
                if (!(details instanceof HTMLDetailsElement)) return;
                // If we're closing and the URL hash points inside this fold,
                // clear the hash first so the browser doesn't force it open.
                if (!details.open) return;
                const raw = window.location.hash || "";
                const id = raw.startsWith("#") ? raw.slice(1) : raw;
                if (!id) return;
                const target = details.querySelector(`#${CSS.escape(id)}`);
                if (!target) return;
                history.replaceState(
                  null,
                  "",
                  window.location.pathname + window.location.search,
                );
              }}
            >
              <span class="foldbox__caret" aria-hidden="true"></span>
              <span class="foldbox__h2 md-output">
                {@html item.heading.html}
              </span>
            </summary>
            <div class="foldbox__body foldbox__body--h2">
              {#each buildH3Sections(item.children) as sub, j (j)}
                {#if sub.type === "chunk"}
                  {#if sub.chunk.type === "callout" && isPinnedTakeaway(sub.chunk)}
                    <div class="foldbox__pin">
                      <CalloutBox
                        variant={sub.chunk.variant}
                        title={sub.chunk.title}
                        html={toHtml(sub.chunk.content)}
                      />
                    </div>
                  {:else if sub.chunk.type === "text"}
                    <div class="md-output">{@html toHtml(sub.chunk.content)}</div>
                  {:else if sub.chunk.type === "jumpbox"}
                    <Jumpbox id={sub.chunk.id} label={sub.chunk.label} />
                  {:else if sub.chunk.type === "small"}
                    <div class="md-output text-sm sm-block">{@html toHtml(sub.chunk.content)}</div>
                  {:else if sub.chunk.type === "callout"}
                    <CalloutBox
                      variant={sub.chunk.variant}
                      title={sub.chunk.title}
                      html={toHtml(sub.chunk.content)}
                    />
                  {:else if sub.chunk.type === "fold"}
                    <FoldBox title={sub.chunk.title} open={sub.chunk.open} html={toHtml(sub.chunk.content)} />
                  {/if}
                {:else if sub.type === "subsection"}
                  <details
                    class="foldbox foldbox--h3"
                    data-h3fold="1"
                    open={shouldOpenH3(sub)}
                    on:toggle={(e) => {
                      const details = e.currentTarget;
                      if (!(details instanceof HTMLDetailsElement)) return;
                      const caret = details.querySelector(".foldbox__caret");
                      if (!(caret instanceof HTMLElement)) return;
                      caret.style.transform = details.open ? "rotate(90deg)" : "rotate(0deg)";
                    }}
                  >
                    <summary
                      class="foldbox__summary foldbox__summary--h3"
                      on:click={(e) => {
                        if (typeof window === "undefined") return;
                        const details = e.currentTarget.parentElement;
                        if (!(details instanceof HTMLDetailsElement)) return;
                        // If we're closing and the URL hash points inside this fold,
                        // clear the hash first so the browser doesn't force it open.
                        if (!details.open) return;
                        const raw = window.location.hash || "";
                        const id = raw.startsWith("#") ? raw.slice(1) : raw;
                        if (!id) return;
                        const target = details.querySelector(`#${CSS.escape(id)}`);
                        if (!target) return;
                        history.replaceState(
                          null,
                          "",
                          window.location.pathname + window.location.search,
                        );
                      }}
                    >
                      <span class="foldbox__caret" aria-hidden="true"></span>
                      <span class="foldbox__h3 md-output">
                        {@html sub.heading.html}
                      </span>
                    </summary>
                    <div class="foldbox__body foldbox__body--h3">
                      {#each sub.children as chunk, k (k)}
                        {#if chunk.type === "callout" && isPinnedTakeaway(chunk)}
                          <div class="foldbox__pin">
                            <CalloutBox
                              variant={chunk.variant}
                              title={chunk.title}
                              html={toHtml(chunk.content)}
                            />
                          </div>
                        {:else if chunk.type === "text"}
                          <div class="md-output">{@html toHtml(chunk.content)}</div>
                        {:else if chunk.type === "jumpbox"}
                          <Jumpbox id={chunk.id} label={chunk.label} />
                        {:else if chunk.type === "small"}
                          <div class="md-output text-sm sm-block">{@html toHtml(chunk.content)}</div>
                        {:else if chunk.type === "callout"}
                          <CalloutBox
                            variant={chunk.variant}
                            title={chunk.title}
                            html={toHtml(chunk.content)}
                          />
                        {:else if chunk.type === "fold"}
                          <FoldBox title={chunk.title} open={chunk.open} html={toHtml(chunk.content)} />
                        {/if}
                      {/each}
                    </div>
                  </details>
                {/if}
              {/each}
            </div>
          </details>
        {/if}
      {/each}
    </div>

    {#if footnotes.length}
      <aside class="md-footnotes" bind:this={footnoteAside} aria-label="Footnotes">
        <ol bind:this={footnoteList}>
          {#each footnotes as fn}
            <li id={`fn-${fn.safeId}`} title={fn.id}>
              <span class="fn-label">{fn.num}</span>
              <span class="fn-text">{@html fn.html}</span>
            </li>
          {/each}
        </ol>
      </aside>
    {/if}
  </div>
</div>

<style lang="postcss">
  /* Nicer anchor landings for figures when navigating via hash/links. */
  :global(.md-output [id^="fig-"]) {
    scroll-margin-top: 120px;
  }

  /* Figure captions: small, gray, left-aligned, full width (match main text column). */
  :global(.md-output .md-figcaption) {
    width: 100%;
    max-width: 100%;
    display: block;
    text-align: left;
    margin-bottom: 1rem;
    color: rgb(107 114 128); /* gray-500 */
    font-size: 0.875rem; /* text-sm */
    line-height: 1.25rem;
    /* Override legacy padding classes in the generated HTML. */
    padding-left: 0 !important;
    padding-right: 0 !important;
  }

  /* Table captions sit right under the table (which keeps its own bottom margin). */
  :global(.md-output .md-tablecaption) {
    margin-top: -0.5rem;
  }

  /* 2x2 figure grid (used in some markdown sections) */
  :global(.md-output .md-figgrid-2x2) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 18px;
    align-items: start;
    margin: 0 0 1rem 0;
  }
  @media (max-width: 800px) {
    :global(.md-output .md-figgrid-2x2) {
      grid-template-columns: 1fr;
    }
  }
  :global(.md-output .md-figgrid-2x2 figure) {
    margin: 0;
  }
  :global(.md-output .md-figgrid-2x2 img) {
    width: 100%;
    height: auto;
    display: block;
    border-radius: 0.25rem;
  }
  :global(.md-output .md-figgrid-2x2 figcaption) {
    margin-top: 0.35rem;
    font-size: 0.875rem;
    line-height: 1.25rem;
    color: rgb(107 114 128); /* gray-500 */
  }

  :global(.md-output h1) {
    @apply text-3xl font-bold mt-6 mb-4;
  }
  :global(.md-output h2) {
    @apply text-[1.1rem] font-semibold mt-5 mb-3;
  }
  :global(.md-output h3) {
    @apply text-lg font-semibold mt-4 mb-2;
  }
  :global(.md-output h4) {
    @apply text-base font-semibold mt-3 mb-2;
  }

  :global(.md-output p) {
    @apply mb-4;
  }
  :global(.md-output strong) {
    @apply font-semibold;
  }
  /* Highlighted (bold) text in running prose is coloured, like the ::blue[]:: highlights
     of the reference post, in CMU red (Carnegie Red #C41230). Captions, coloured spans, tables, headings and
     short run-in labels (<strong class="md-runin">, added by scripts/notion/postprocess.py)
     and passages listed in scripts/notion/plain.txt (<strong class="md-plain">) keep the normal ink colour. */
  :global(.md-output p strong),
  :global(.md-output li strong) {
    color: var(--md-highlight, #c41230); /* Carnegie Red */
  }
  :global(.md-output .md-figcaption strong),
  :global(.md-output span[style*="color"] strong),
  :global(.md-output strong.md-runin),
  :global(.md-output strong.md-plain) {
    color: inherit;
  }
  :global(.md-output em) {
    @apply italic;
  }
  :global(.md-output code) {
    @apply text-[95%] bg-neutral-100 px-1 rounded;
  }

  :global(.md-output pre) {
    @apply bg-neutral-100 p-4 rounded overflow-x-auto mb-4;
  }

  :global(.md-output ul) {
    @apply list-disc list-outside ml-5 pl-5 mb-4 space-y-1;
  }
  :global(.md-output ol) {
    @apply list-decimal list-outside ml-5 pl-5 mb-4 space-y-1;
  }

  :global(.md-output li) {
    @apply mb-1;
  }

  /* Tables (Markdown) */
  :global(.md-output table) {
    @apply w-full text-[95%] mb-4;
    border-collapse: collapse;
    display: block; /* enable horizontal scrolling on narrow viewports */
    overflow-x: auto;
    max-width: 100%;
  }
  :global(.md-output thead) {
    @apply bg-neutral-50;
  }
  :global(.md-output th),
  :global(.md-output td) {
    @apply align-top px-3 py-2;
    border: 1px solid rgb(229 231 235); /* neutral-200 */
  }
  :global(.md-output th) {
    @apply text-left font-semibold text-neutral-800;
    /* Headers may wrap, so tables with long headers (e.g. "Cumulative reward (9 + 9 + 9)")
       fit the text column instead of scrolling sideways. */
    white-space: normal;
  }
  :global(.md-output tbody tr:nth-child(even)) {
    @apply bg-neutral-50/50;
  }
  /* Notion row background colours, for raw HTML tables written as <tr class="nbg-…">
     (scripts/notion/postprocess.py). Painted on the cells so they win over the zebra rows. */
  :global(.md-output tr.nbg-gray > *) { background: #f1f1ef; }
  :global(.md-output tr.nbg-brown > *) { background: #f4eeee; }
  :global(.md-output tr.nbg-orange > *) { background: #fbecdd; }
  :global(.md-output tr.nbg-yellow > *) { background: #fbf3db; }
  :global(.md-output tr.nbg-green > *) { background: #edf3ec; }
  :global(.md-output tr.nbg-blue > *) { background: #e7f3f8; }
  :global(.md-output tr.nbg-purple > *) { background: #f4f0f7; }
  :global(.md-output tr.nbg-pink > *) { background: #f9eef3; }
  :global(.md-output tr.nbg-red > *) { background: #fdebec; }

  :global(.math-block) {
    @apply my-4 text-center;
    /* A long equation scrolls inside its own box instead of widening the page
       (page-level horizontal scroll also confuses the TOC/sidenote logic). */
    overflow-x: auto;
    overflow-y: hidden;
  }
  :global(.math-inline) {
    @apply align-baseline;
  }
  :global(.katex-error) {
    @apply text-red-600 bg-red-100 p-1 rounded;
  }
  :global(.md-output blockquote) {
    @apply inline-block align-middle bg-neutral-50 rounded px-3 py-2 my-2 border-l-4 border-neutral-600;
  }
  :global(.md-output blockquote > :first-child) {
    @apply mt-0;
  }
  :global(.md-output blockquote > :last-child) {
    @apply mb-0;
  }

  /* Auto-folded H2 sections */
  :global(details.foldbox.foldbox--h2) {
    @apply my-4;
  }

  :global(details.foldbox.foldbox--h2 > .foldbox__summary) {
    /* folder-entry style with clickable area */
    @apply px-0 py-1 cursor-pointer select-none;
  }

  :global(details.foldbox.foldbox--h2 > .foldbox__body) {
    @apply pl-6 pt-2;
  }

  :global(details.foldbox.foldbox--h2 .foldbox__h2 > h2) {
    /* remove the default h2 margins since it's now inside <summary> */
    margin: 0;
  }

  /* Important: the H2 is rendered as real HTML inside <summary>.
     Let the h2 container receive clicks, but not its children. */
  :global(details.foldbox.foldbox--h2 .foldbox__h2) {
    /* Allow the wrapper to receive clicks */
    pointer-events: auto;
  }
  :global(details.foldbox.foldbox--h2 .foldbox__h2 h2),
  :global(details.foldbox.foldbox--h2 .foldbox__h2 h2 *) {
    /* Prevent h2 and its children from intercepting clicks */
    pointer-events: none;
  }

  /* Shared caret styling for h2/h3 folds (self-contained, no FoldBox dependency) */
  :global(details.foldbox > summary::-webkit-details-marker) {
    display: none;
  }
  :global(.foldbox__caret) {
    width: 0;
    height: 0;
    border-top: 6px solid transparent;
    border-bottom: 6px solid transparent;
    border-left: 7px solid currentColor;
    transform: rotate(0deg);
    transform-origin: 2px 6px;
    transition: transform 120ms ease;
    opacity: 0.9;
    flex: 0 0 auto;
  }
  :global(details.foldbox[open] .foldbox__caret) {
    transform: rotate(90deg);
  }

  /* Auto-folded H3 sections inside H2 folds */
  :global(details.foldbox.foldbox--h3) {
    @apply my-2;
  }

  :global(details.foldbox.foldbox--h3 > .foldbox__summary) {
    @apply px-0 py-1 pl-4 cursor-pointer select-none text-sm font-semibold text-neutral-800;
    @apply flex items-center gap-2;
  }

  :global(details.foldbox.foldbox--h3 > .foldbox__body) {
    @apply pl-8 pt-2;
  }

  :global(details.foldbox.foldbox--h3 .foldbox__h3 > h3) {
    margin: 0;
  }

  :global(details.foldbox.foldbox--h3 .foldbox__h3 h3),
  :global(details.foldbox.foldbox--h3 .foldbox__h3 h3 *) {
    pointer-events: none;
  }

  /* Keep pinned takeaways visible even when the fold is closed */
  :global(details.foldbox > .foldbox__body .foldbox__pin) {
    display: block;
  }

  :global(details.foldbox.foldbox--h3 > summary .foldbox__caret) {
    transform: rotate(0deg);
  }
  :global(details.foldbox.foldbox--h3[open] > summary .foldbox__caret) {
    transform: rotate(90deg) !important;
  }

  /* Small-section overrides: drop each heading one step inside .sm-block */
  /* :global(.sm-block) { font-size: 0.875rem; } */
  :global(.sm-block h1) { @apply text-2xl font-bold mt-6 mb-4; }
  :global(.sm-block h2) { @apply text-base font-semibold mt-5 mb-3; }
  :global(.sm-block h3) { @apply text-sm font-semibold mt-4 mb-2; }
  :global(.sm-block h4) { @apply text-xs font-semibold mt-3 mb-2; }
  /* Make inline code a touch smaller relative to the smaller text size */
  :global(.sm-block code) { @apply text-[90%]; }
  /* Optional: tighten paragraphs slightly in small blocks */
  /* :global(.sm-block p) { @apply mb-3; } */

  .md-shell {
    position: relative;
  }

  /* Hide footnotes until we've aligned them once to avoid initial flash at top.
     NOTE: data-fn-aligned / data-side are set from JS, so selectors that test
     them must be :global(...). Otherwise Svelte prunes them as "unused" -- which
     is what happened in the original template: its data-side rules never
     reached the built CSS. */
  .md-shell:not([data-fn-aligned="1"]) .md-footnotes {
    opacity: 0;
  }
  :global(.md-shell[data-fn-aligned="1"] .md-footnotes) {
    opacity: 1;
    transition: opacity 120ms ease;
  }

  .md-grid {
    display: grid;
    /* 3 columns: left margin | main text | right margin (footnotes live in the right margin) */
    /* the left track is never narrower than the fixed TOC (--toc-reserve, set by ScrollMeter) */
    grid-template-columns: minmax(var(--toc-reserve, 0px), 1fr) minmax(0, var(--md-main-col, 760px)) minmax(0, 1fr);
    column-gap: var(--toc-gap, var(--side-gap, 32px));
    align-items: start;
  }

  /* data-side="off" is published by ScrollMeter when 760px / viewport >= 0.615
     (viewport <= ~1236px): no TOC, no margin. Collapse to one column, keep the
     text at the normal column width, and show footnotes as a "Notes" list
     after the article instead of hiding them.
     ".md-shell.md-shell" is deliberate: Svelte compiles the base rules below to
     ".md-output.svelte-xyz.svelte-xyz" (specificity 0,3,0), so these need 0,4,0. */
  :global(.md-shell.md-shell[data-side="off"] .md-grid) {
    grid-template-columns: minmax(0, 1fr);
    row-gap: 16px;
  }
  :global(.md-shell.md-shell[data-side="off"] .md-grid > .md-output),
  :global(.md-shell.md-shell[data-side="off"] .md-grid > .md-footnotes) {
    grid-column: 1;
    width: 100%;
    max-width: 760px; /* keep in sync with --md-main-col default */
    justify-self: center;
  }
  :global(.md-shell.md-shell[data-side="off"] .md-grid > .md-footnotes) {
    position: static;
    padding-left: 0;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid rgb(229 231 235);
    opacity: 1;
  }
  :global(.md-shell.md-shell[data-side="off"] .md-footnotes::before) {
    content: "Notes";
    display: block;
    font-weight: 600;
    color: #374151;
    margin-bottom: 0.5rem;
  }
  :global(.md-shell.md-shell[data-side="off"] .md-footnotes li) {
    display: flex !important;
    position: static !important;
    top: auto !important;
    margin-bottom: 0.6rem;
  }

  /* Keep main text centered and at a readable width, regardless of footnotes. */
  .md-output {
    grid-column: 2;
    min-width: 0;
  }

  .md-footnotes {
    position: relative;
    grid-column: 3;
    width: min(260px, 100%); /* shrink with the margin track instead of overflowing it */
    justify-self: start;
    padding-left: calc(var(--footnote-gap, 48px) - var(--toc-gap, var(--side-gap, 32px)));
    font-size: 13px;
    line-height: 1.6;
    color: #6b7280;
  }

  .md-footnotes ol {
    list-style: none;
    padding: 0;
    margin: 0;
    position: relative;
    min-height: 100%;
  }

  .md-footnotes li {
    display: flex;
    gap: 8px;
    width: 100%;
    margin-bottom: var(--footnote-item-gap, 28px);
  }
  .md-footnotes li:last-child {
    margin-bottom: 0;
  }

  .md-footnotes .fn-label {
    font-variant-numeric: tabular-nums;
    color: #6b7280;
  }

  .md-footnotes .fn-text :global(p) {
    margin: 0;
  }

  .md-footnotes .fn-text {
    min-width: 0; /* allow flex child to shrink so wrapping can happen */
  }

  .md-footnotes .fn-text :global(a) {
    @apply underline underline-offset-[3px] decoration-neutral-400;
    /* Allow very long URLs to wrap nicely in the right-side footnote panel. */
    overflow-wrap: anywhere;
    word-break: break-word;
    hyphens: auto;
  }

  :global(.footnote-ref) {
    font-size: 0.75em;
    vertical-align: super;
    margin-left: 1px;
  }

  :global(.footnote-ref a) {
    color: #6b7280;
    text-decoration: none;
  }

  :global(.footnote-ref a:hover) {
    color: #111827;
  }

  @media (max-width: 1024px) {
    .md-grid {
      grid-template-columns: minmax(0, 1fr);
      row-gap: 16px;
    }
    .md-output {
      grid-column: 1;
    }
    .md-grid > .md-output {
      width: 100%;
      max-width: 760px;
      justify-self: center;
    }
    .md-footnotes {
      position: static;
      grid-column: 1;
      width: auto;
    }
  }

  :global(pre[data-copyable]) {
    position: relative;
  }

  :global(pre[data-copyable] .copy-btn) {
    position: absolute;
    top: 0.25rem;
    right: 0.25rem;
    background: #f3f4f6; /* neutral-100 */
    font-size: 0.75rem;
    padding: 0.1rem 0.4rem;
    border-radius: 0.25rem;
    cursor: pointer;
    opacity: 1;
    transition: opacity 0.2s;
  }

  :global(pre[data-copyable]:hover .copy-btn) {
    opacity: 1;
  }

</style>
