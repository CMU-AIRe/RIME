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

<header
  class="layout-xl justify-between items-start"
  data-sveltekit-noscroll
  data-sveltekit-preload-code="eager"
>
  <div class="header-inner mb-8">
    <h1 class="title-font font-bold text-black text-3xl mb-4 leading-tight">
      {meta.title ?? ""}
    </h1>
    {#if meta.subtitle}
      <p class="subtitle text-neutral-600 mb-4">{meta.subtitle}</p>
    {/if}

    <div class="meta text-black">
      {#if meta.authors?.length}
        <div class="authors">
          {#each meta.authors as author, i (i)}
            <span class="author">
              {#if author.url}
                <a class="author-name link-no-underline" href={author.url} target="_blank" rel="noopener noreferrer"
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
            </span>
          {/each}
        </div>
      {/if}

      {#if affiliations.length}
        <div class="affiliations">
          {#each affiliations as line, i (i)}
            <span class="affiliation-item">
              {#if numbered}<sup>{i + 1}</sup>{/if}{line}
            </span>
          {/each}
        </div>
      {/if}

      {#if meta.notes?.length}
        <div class="notes">
          {#each meta.notes as note, i (i)}
            <span class="note-item">{note}</span>
          {/each}
        </div>
      {/if}

      {#if meta.date || meta.github_url}
        <div class="date">
          {#if meta.date}<span>{meta.date}</span>{/if}
          {#if meta.github_url}
            <a class="link ml-3" href={meta.github_url} target="_blank" rel="noopener noreferrer">Code</a>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</header>

<style lang="postcss">
  /* Keep the header aligned with the same main-text column width used by Markdown.svelte. */
  .header-inner {
    max-width: var(--md-main-col, 760px);
    margin-left: auto;
    margin-right: auto;
  }

  .title-font {
    font-family: "Iowan Old Style BT", "Iowan Old Style", "Palatino Linotype", Palatino, serif;
  }

  .subtitle {
    font-size: 1.15rem;
    line-height: 1.5;
  }

  .meta {
    font-size: 16px;
    line-height: 1.55;
  }

  .authors {
    font-size: 16px;
    line-height: 2;
    text-align: center;
  }

  .author {
    display: inline-flex;
    align-items: baseline;
    gap: 1px;
    margin-right: 8px;
    margin-bottom: 4px;
    white-space: nowrap;
  }

  .author-name {
    line-height: 1.4;
  }

  .affil-sup {
    font-size: 11px;
    margin-left: 1px;
  }

  .affiliations,
  .notes {
    margin-top: 10px; /* visual separation from authors */
    color: #111827;
    opacity: 0.9;
    text-align: center;
  }

  .notes {
    margin-top: 2px;
    font-size: 14px;
  }

  .affiliation-item,
  .note-item {
    display: inline-block;
    margin: 0 8px;
  }

  .date {
    margin-top: 10px;
    color: #111827;
    opacity: 0.9;
  }

  @media (max-width: 580px) {
    .meta {
      font-size: 15px;
    }
  }
</style>
