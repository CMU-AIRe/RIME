# Layout notes

How the page is put together, what each piece of syntax turns into, how it
reflows, and where to change things. Everything here was read off the CSS and
JS (no browser was run on the build machine), so check the items marked
*(unverified)* on a real screen. Syntax reference: [README.md](README.md#markdown-cheat-sheet).

## Page structure

Top to bottom, one route (`/`, i.e. `https://cmu-aire.github.io/RIME/`):

1. **Body.** Vertical padding 48px, 96px from 640px wide, 128px from 768px
   (`src/app.css`, `body`). Text colour `#404040` (Tailwind `neutral-700`).
2. **Optional logo**, absolutely positioned top right (`meta.json` → `logo`;
   `src/routes/+layout.svelte`). Not set by default.
3. **Title block** (`src/lib/components/Header.svelte`, data from
   `src/maintext/meta.json`): inside the 1200px container, capped to the text
   column width (`--md-main-col`, 760px). Title 30px bold, left-aligned; optional
   subtitle; author line, affiliation line and notes line centred; date (and
   "Code" link if `github_url`) left-aligned.
4. **Left TOC** (`src/lib/components/ScrollMeter.svelte`, despite the name: it
   is a text TOC, not the gradient progress bar the old docs describe). Fixed at
   18px from the left edge, 24px from top and bottom, up to ~200-320px wide (it
   shrinks to the space left of the text column), scrolls on its own. Lists every
   `h2`/`h3` inside the article; the current one is bold. When the mouse is not
   over it, only the current `##` section's entries are visible (the others keep
   their space but are hidden). Clicking an entry opens any folded parent and
   scrolls there. Only shown when the window is wider than ~1236px (below).
5. **Article** (`src/lib/components/Markdown.svelte`): a 3-column grid inside the
   1200px container (`.layout-xl`, 16px side padding, 24px from 640px):
   `[1fr | text column ≤ 760px | 1fr]`, 44px gaps. The text column is
   `--md-main-col`, which the TOC script sets to `min(760, max(520, viewport −
   TOC width − gaps))`.
6. **Sidenotes**: footnotes live in the right grid column, 260px wide, 13px gray,
   each moved by JS to the height of the line that cites it, pushed down to keep
   ≥ 28px between notes. Notes whose citation is inside a closed fold are hidden.
7. **Footer**: only a "Source on GitHub" link, and only when `github_url` is set.

## What the syntax renders to

| Source | Output |
|---|---|
| text before the first `##` | plain block, not collapsible |
| `## Heading` | `<details class="foldbox foldbox--h2" open>` whose `<summary>` holds the `h2` (17.6px semibold) and a caret; body indented 24px |
| `### Heading` | nested `<details class="foldbox foldbox--h3" open>`; summary indented 16px, body indented a further 32px (so `###` text sits 56px right of `##` headings) |
| `####` / `#` | plain `h4` (16px semibold) / `h1` (30px bold); no fold, no TOC entry |
| paragraph | `<p>` with 16px bottom margin; 16px/24px text |
| `$…$` / `$$…$$` | KaTeX HTML rendered at build time (`span.math-inline` / `div.math-block`, centred; wide equations scroll inside the box). Bad TeX shows in red |
| image + title | `<img class="block mx-auto">` (centred, never wider than the column) + `div.md-figcaption` (14px gray, left-aligned, full column width, leading "Figure N:" bold) |
| image `{attrs}` | same, with the attributes copied onto `<img>`; `.mp4/.webm/.ogg` become `<video muted playsinline>` that play when 100% visible |
| `<div class="md-figgrid-2x2">` | 2-column CSS grid of `<figure>`s, 18px gap, 1 column below 800px |
| GFM table | full-width table, 95% font, gray borders, gray header, zebra rows; becomes horizontally scrollable when too wide (header cells never wrap) |
| fenced code | gray `pre`, horizontal scroll, "Copy" button top right (added in the browser) |
| `` `code` `` | gray rounded inline box, 95% size |
| `> quote` | gray *inline-block* box with a dark 4px left border, as wide as its text (not a full-width quote) |
| lists | disc / decimal markers, outside, 40px indent |
| `[^id]` | `<sup class="footnote-ref"><a href="#fn-id">N</a></sup>`, gray; the note itself goes to the sidenote column (or the "Notes" list) |
| `::color[…]::` | `<span style="color:#…">` with Notion's palette |
| `:::callout_begin type=…:::` | rounded box with a 4px left border and a small uppercase label: note = slate, info = sky, tip = emerald, warning = amber, takeaway = brown (`#EFE6DC` / `#5A3E33`) |
| `:::takeaway_begin:::` | takeaway callout, label "Takeaways" |
| `:::fold_begin …:::` | `<details class="foldbox foldbox--boxed">`: light gray box with border, semibold 16px summary + caret, closed unless `open` |
| `:::small_begin:::` | `div.text-sm.sm-block` (see quirks: same size as body text) |
| `:::jumpbox …:::` | full-width gray link box `↪ label` to `#id` |
| `<iframe>` / other raw HTML | passed through unchanged (root-absolute `src`/`href` get the base path) |
| "Figure N" / "Fig. N" in text | linked to the figure whose caption starts with "Figure N" (browser only) |

## Responsive behaviour

The switch between the two layouts is made in JS by ScrollMeter, not by a CSS
breakpoint: if `760 / viewport width ≥ 0.615` (viewport ≤ ~1236px) it sets
`<html data-sidecols="off">`, and Markdown copies that to `data-side="off"`.

| Viewport | Layout |
|---|---|
| > ~1236px | TOC on the left, 760px text column, sidenotes on the right |
| ≤ ~1236px | no TOC; one centred column ≤ 760px; footnotes as a numbered "Notes" list after the article |
| ≤ 1024px | same, also enforced by a CSS media query |
| ≤ 800px | `md-figgrid-2x2` stacks to one column |
| ≤ 720px | logo (if any) shrinks |
| < 640px | container side padding 16px (24px above); body top padding 48px |
| ≤ 580px | title-block text 15px |

On a 375px phone: container padding leaves 343px; `##` body text gets 319px,
`###` body text 287px (the fold indents). Tables, code, and wide equations
scroll sideways inside their boxes; images scale down. Videos autoplay only when
100% visible, so a video taller than the screen never starts. Page transitions
are disabled for Android/iPhone user agents and reduced-motion users.

## Typography and colour

- **Fonts.** Body and title use the system serif stack `"Iowan Old Style BT",
  "Iowan Old Style", "Palatino Linotype", Palatino, serif`: Iowan on
  macOS/iOS, Palatino Linotype on Windows, the default serif (DejaVu/Noto Serif)
  on Linux and Android. No webfont is shipped. Math uses KaTeX's own fonts
  (bundled, ~60 files, loaded on demand).
- **Sizes.** `body` sets 17.7px / 1.7, but the article wrapper has Tailwind
  `text-base`, so article text is **16px / 24px**. Letter-spacing 0.025em.
  `h2` 17.6px, `h3` 18px, figure captions 14px, sidenotes and TOC 13px, callout
  labels 12px. `tailwind.config.js` redefines `text-sm` as 16px / 22.4px and
  `text-xl` as 20.8px / 32px.
- **Colours.** Text `#404040`; title and headings black; links underlined in
  `#a3a3a3`, black on hover; TOC and sidenotes `#6b7280`, active TOC item
  `#111827`; text selection `sky-100`; fold and table chrome `neutral-50` fills
  with `neutral-200` borders. Coloured text uses Notion's colours (gray
  `#9B9A97`, brown `#64473A`, orange `#D9730D`, yellow `#DFAB01`, green
  `#0F7B6C`, blue `#0B6E99`, purple `#6940A5`, pink `#AD1A72`, red `#E03E3D`).
  There is no dark mode.

## Knobs

| Change | Where |
|---|---|
| Title, authors, affiliations, date, code link, logo, `<title>`/description | `src/maintext/meta.json` |
| Title block look | `src/lib/components/Header.svelte` (`<style>`) |
| Text column width (760px) | keep in sync: `Markdown.svelte` (`.md-grid` default and the two `max-width: 760px` rules), `ScrollMeter.svelte` (`MAIN_MAX_PX`, `baseMain`), `Header.svelte` (`.header-inner`) |
| Outer container width (1200px) / footer width (780px) | `src/app.css` `.layout-xl` / `.layout-md` |
| Gaps between TOC, text and sidenotes | `src/app.css` `:root` (`--toc-gap`, `--footnote-gap`, `--footnote-item-gap`, `--toc-min-left`) |
| Sidenote width (260px), size, colour | `Markdown.svelte` `.md-footnotes` |
| When the TOC/sidenotes switch off | `ScrollMeter.svelte` `RATIO_HIDE` / `RATIO_SHOW`; TOC max width `tocMaxWidthCap` |
| Body font / size | `src/app.css` `body`; article size is the `text-base` class in `src/routes/+page.svelte` |
| Heading sizes, fold indents, tables, code, blockquote, captions | `Markdown.svelte` `<style>` (`.md-output h2`, `.foldbox__body--h2/h3`, ...) |
| Callout colours and default labels | `src/lib/components/CalloutBox.svelte` (`styles`) |
| Fold box look | `src/lib/components/FoldBox.svelte` |
| Which `###` start open | `shouldOpenH3` in `Markdown.svelte` (now: all) |
| Notion colour palette | `colorText` in `Markdown.svelte` |
| Favicon | `static/favicon.svg` (placeholder), linked from `src/app.html` |
| Analytics | none; add a script to `src/app.html` if wanted |

## Broken or awkward in the template

### Fixed while porting

- **Footnotes disappeared on narrow screens.** Below ~1236px they were never
  shown (the notes stayed at opacity 0 or were stacked unaligned). They now
  become a "Notes" list after the article. *(unverified)*
- **The narrow-layout CSS never shipped.** All `data-side="off"` rules were
  stripped by Svelte as "unused selectors" (the attribute is only set from JS);
  this is also true of the live reference site. They are now `:global(...)`.
  *(unverified)*
- **Text ran the full container width at ≤ 1024px** (up to ~976px lines on
  tablets). The single column is now capped at 760px and centred. *(unverified)*
- **All `###` sections started collapsed** except ones titled "Question N". They
  now start open.
- **Code was not protected from the pre-parsers**: a `## comment` line in a code
  block became a section, a regex like `[^a-z]` became a footnote, and
  `:::…:::` shown as an example became a real box. Code blocks and inline code
  are now skipped.
- **Wide display equations** could widen the page, which also flipped the TOC
  logic into "side columns on" on phones. They now scroll inside their box.
- Root-absolute URLs (`/assets/...`) broke under `/RIME/`; missing `.png`/`.jpg`
  were silently ignored at build time; Google Analytics IDs from the reference
  were embedded; two fonts were preloaded but never used; every KaTeX font was
  preloaded; a global `code { font-size: 10rem }` rule; the jumpbox ignored its
  `label` and said "Our paper:"; 14 TypeScript errors; `marked`'s
  `smartypants` option was passed but does nothing in marked 12 (removed; quotes
  and dashes are output exactly as typed).

### Still open (decide before content goes in)

- **Sidenote column overflows at common laptop widths** *(unverified,
  computed)*: the right grid track is only ~152px (1200px container − 760px
  column − gaps), but the notes are 260px wide and spill rightwards into the
  page margin. That fits only from ~1368px; between ~1237px and ~1367px (1280-
  and 1366-pixel laptops) the page likely gets a horizontal scrollbar. Options:
  widen `.layout-xl` to ~1320px, narrow `.md-footnotes` to ~200px, or raise the
  switch-off threshold.
- **Heading hierarchy is carried by indentation, not size**: `h2` (17.6px) is
  slightly smaller than `h3` (18px), and both are close to body text (16px).
- **Deep indentation on phones**: `###` text starts 56px right of the column
  edge (287px of text on a 375px phone).
- **`small` is not smaller**: `text-sm` is redefined as 16px in
  `tailwind.config.js`, so `:::small_begin:::` only tightens line height.
- **`type="info"` callouts are labelled "Takeaways"** unless given a `title`.
- **A takeaway inside a `###` ends that subsection**: following text jumps back
  to the `##` indentation.
- **Blockquotes are inline-block** boxes sized to their text, not full-width
  quotes.
- **Title block alignment is mixed**: title and date left, authors and
  affiliations centred.
- **Body font differs by OS** (no webfont). Linux/Android readers get a generic
  serif.
- **Client JS is ~360 kB (110 kB gzipped)**: marked and KaTeX ship to the
  browser and the whole post is re-rendered during hydration, although the HTML
  is already prerendered. Fine for one post; a long post with many equations
  will cost some CPU on load.
- **TOC accessibility**: the TOC is `aria-hidden` but its links are focusable.
- **Duplicate figure ids**: an image's anchor is `fig-<slug of alt text>`, so
  two images with the same alt text share an id; give one an `{id=…}`.
- **Pinned toolchain**: SvelteKit 2.5, Vite 5.1, Svelte 4 as in the reference;
  `npm audit` lists build-tool advisories (none affect the static output's
  runtime beyond what is above). Upgrading SvelteKit/Vite within the same major
  is possible but untested; marked must stay on 12.x (the renderer uses the
  pre-13 API).
