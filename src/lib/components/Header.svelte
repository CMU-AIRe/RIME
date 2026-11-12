<script lang="ts">
  import { meta } from "$lib/meta";
  import type { Author } from "$lib/meta";

  const affiliations = meta.affiliations ?? [];
  // Superscript numbers are only useful when there is more than one affiliation.
  const numbered = affiliations.length > 1;

  const affilList = (a: Author) =>
    a.affiliation == null ? [] : Array.isArray(a.affiliation) ? a.affiliation : [a.affiliation];

  function affilNums(a: Author): number[] {
    return affilList(a)
      .map((name) => affiliations.indexOf(name) + 1)
      .filter((n) => n > 0);
  }

  // Convention kept from the original template: a trailing "*" on a name marks
  // equal contribution and is rendered as a superscript.
  const stripStar = (name: string) => name.replace(/\*+$/, "").trim();
  const hasStar = (name: string) => /\*$/.test(name);
</script>

<header class="layout-xl" data-sveltekit-noscroll data-sveltekit-preload-code="eager">
  <div class="header-grid">
    <div class="header-inner">
      <h1 class="title">{meta.title ?? ""}</h1>
      {#if meta.subtitle}
        <p class="subtitle">{meta.subtitle}</p>
      {/if}

      <!-- Byline: small-caps labels over values, between two hairlines. -->
      <dl class="byline">
        {#if meta.authors?.length}
          <div class="byline-col byline-authors">
            <dt>{meta.authors.length > 1 ? "Authors" : "Author"}</dt>
            <dd>
              <ul class="author-list">
                {#each meta.authors as author, i (i)}
                  <li class="author">
                    {#if author.url}
                      <a class="author-name" href={author.url} target="_blank" rel="noopener noreferrer"
                        >{stripStar(author.name)}</a
                      >
                    {:else}
                      <span class="author-name">{stripStar(author.name)}</span>
                    {/if}
                    {#if (numbered && affilNums(author).length) || hasStar(author.name)}
                      <sup class="affil-sup"
                        >{numbered ? affilNums(author).join(",") : ""}{hasStar(author.name) ? "*" : ""}</sup
                      >
                    {/if}
                  </li>
                {/each}
              </ul>
            </dd>
          </div>
        {/if}

        {#if affiliations.length}
          <div class="byline-col">
            <dt>{affiliations.length > 1 ? "Affiliations" : "Affiliation"}</dt>
            <dd>
              {#each affiliations as line, i (i)}
                <div class="affiliation-item">{#if numbered}<sup>{i + 1}</sup>{/if}{line}</div>
              {/each}
            </dd>
          </div>
        {/if}

        {#if meta.date}
          <div class="byline-col">
            <dt>Published</dt>
            <dd>{meta.date}</dd>
          </div>
        {/if}

        {#if meta.github_url}
          <div class="byline-col">
            <dt>Code</dt>
            <dd><a class="code-link" href={meta.github_url} target="_blank" rel="noopener noreferrer">GitHub</a></dd>
          </div>
        {/if}
      </dl>

      {#if meta.notes?.length}
        <p class="notes">
          {#each meta.notes as note, i (i)}<span class="note-item">{note}</span>{/each}
        </p>
      {/if}
    </div>
  </div>
</header>

<style lang="postcss">
  /* Same three-track grid as .md-grid in Markdown.svelte, so the title block sits exactly
     over the text column: the left track reserves the fixed TOC (--toc-reserve, published by
     ScrollMeter; 0 when the TOC is hidden), and the text column follows --md-main-col. */
  .header-grid {
    display: grid;
    grid-template-columns: minmax(var(--toc-reserve, 0px), 1fr) minmax(0, var(--md-main-col, 760px)) minmax(0, 1fr);
    column-gap: var(--toc-gap, var(--side-gap, 32px));
  }
  .header-inner {
    grid-column: 2;
    min-width: 0;
    padding-top: 56px;
    margin-bottom: 2.5rem;
  }
  /* Narrow screens / TOC hidden: one centred column, like the article. */
  @media (max-width: 1024px) {
    .header-grid { grid-template-columns: minmax(0, 1fr); }
    .header-inner { grid-column: 1; width: 100%; max-width: 760px; justify-self: center; padding-top: 24px; }
  }
  :global(html[data-sidecols="off"]) .header-grid { grid-template-columns: minmax(0, 1fr); }
  :global(html[data-sidecols="off"]) .header-inner {
    grid-column: 1;
    width: 100%;
    max-width: 760px;
    justify-self: center;
  }

  .title {
    font-family: "Iowan Old Style BT", "Iowan Old Style", "Palatino Linotype", Palatino, serif;
    font-weight: 700;
    font-size: clamp(1.9rem, 1.2rem + 2vw, 2.6rem);
    line-height: 1.15;
    letter-spacing: -0.01em;
    color: #111;
    margin: 0 0 0.6rem;
  }

  .subtitle {
    font-size: 1.15rem;
    line-height: 1.5;
    color: #4b5563;
    margin: 0 0 0.5rem;
  }

  /* --- byline ------------------------------------------------------------------- */
  .byline {
    display: flex;
    flex-wrap: wrap;
    column-gap: 3.5rem;
    row-gap: 1rem;
    margin: 1.5rem 0 0;
    padding: 1rem 0 1.1rem;
    border-top: 1px solid #e5e7eb;
    border-bottom: 1px solid #e5e7eb;
  }

  .byline dt {
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 0.35rem;
  }

  .byline dd {
    margin: 0;
    font-size: 16px;
    line-height: 1.55;
    color: #111827;
  }

  .author-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .author {
    white-space: nowrap;
  }

  .author-name {
    color: inherit;
    text-decoration: none;
  }
  a.author-name:hover,
  .code-link:hover {
    color: #c41230; /* Carnegie Red */
  }

  .code-link {
    color: inherit;
    text-decoration: underline;
    text-decoration-color: #d1d5db;
    text-underline-offset: 3px;
  }

  .affil-sup {
    font-size: 11px;
    margin-left: 1px;
  }

  .notes {
    margin: 0.5rem 0 0;
    font-size: 13px;
    color: #6b7280;
  }
  .note-item + .note-item {
    margin-left: 1rem;
  }

  @media (max-width: 580px) {
    .byline {
      flex-direction: column;
      row-gap: 0.75rem;
    }
    .byline dd {
      font-size: 15px;
    }
  }
</style>
