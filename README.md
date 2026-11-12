# RIME blog site

Static site for the blog post *How to Train Memory Writing for Continual Learning*,
served at <https://cmu-aire.github.io/RIME/> (the path is case-sensitive).

SvelteKit 2 + `@sveltejs/adapter-static` + Tailwind 3 + `marked` 12 + KaTeX. The
whole post is **one Markdown file** rendered at build time; the output is plain
static HTML/CSS/JS. Page layout, responsive behaviour and known quirks are in
[LAYOUT_NOTES.md](LAYOUT_NOTES.md).

## Install, develop, build

Requires Node 22 (LTS) and npm.

```sh
npm ci                          # install exactly what package-lock.json pins
npm run dev                     # http://localhost:5173/  (dev always serves at "/")
BASE_PATH=/RIME npm run build   # static site in build/, URLs prefixed for /RIME/
BASE_PATH=/RIME npm run preview # serve build/ at http://localhost:4173/RIME/
npm run check                   # svelte-check (types)
```

`BASE_PATH` must start with `/` and have no trailing slash; leave it unset for a
site served at a domain root. The build **fails** on any broken local image,
iframe or link target (including `#anchors`), so a green build means no 404s.

On the CMU babel login nodes, V8 cannot reserve WebAssembly memory under the
16 GB `ulimit -v`; prefix commands with `NODE_OPTIONS=--disable-wasm-trap-handler`.

## Where things live

| What | Where |
|---|---|
| Post body (the only content file) | `src/maintext/post.md` |
| Title, subtitle, authors, affiliations, date, links, logo | `src/maintext/meta.json` |
| Figures, GIFs, videos | `static/assets/figures/` → write `assets/figures/x.png` in the post |
| Interactive case-study pages | `static/case-studies/` → `case-studies/x.html` |
| Markdown renderer and its extensions | `src/lib/components/Markdown.svelte` |
| Left TOC, sidenote visibility switch | `src/lib/components/ScrollMeter.svelte` |
| Callout / fold / jumpbox boxes | `src/lib/components/{CalloutBox,FoldBox,Jumpbox}.svelte` |
| Global CSS, widths, gaps | `src/app.css` |
| Helper scripts for imported Markdown | `scripts/` (see below) |

`meta.json` fields: `title`; `subtitle` (optional); `description` (optional, for
`<meta name="description">`); `authors`: `[{ "name", "affiliation", "url"? }]`,
where `affiliation` is a string or a list of strings that also appear in
`affiliations` (superscript numbers appear only when there are 2+ affiliations,
and a trailing `*` on a name becomes a superscript star); `affiliations`;
`notes` (optional lines such as `"* Equal contribution"`); `date`;
`github_url` (optional, adds a "Code" link and a footer link); `logo`
(optional `{ "src": "assets/logo.png", "alt": "..." }`, shown top right).

## Markdown cheat-sheet

Standard GitHub-flavoured Markdown (headings, emphasis, lists, task lists,
tables, fenced code, blockquotes, raw HTML) plus the extensions below.
`src/maintext/post.md` currently demonstrates every one of them.

**Paths.** Write site files relative to the site root without a leading slash
(`assets/figures/x.png`, `case-studies/y.html`); they resolve under `/RIME/`.
A leading slash (`/assets/...`) also works: the renderer adds the base path,
in Markdown and in raw HTML `src`/`href` attributes alike.

| Feature | Syntax | Notes |
|---|---|---|
| Section | `## Title` / `### Title` | Collapsible, start open, listed in the left TOC. `####` is a plain heading. Ids are slugs of the text (`## 3. Math` → `#3-math`). |
| Inline math | `$x^2$` | One line only. Any two `$` on one line form math: write a literal dollar as `\$`. |
| Display math | `$$` on its own line, TeX, `$$` on its own line | `\begin{aligned}…\end{aligned}` works. `$$` always means display math, even mid-sentence. |
| Figure + caption | `![alt](assets/figures/x.png "Figure 3: Caption *with* $math$.")` | The title becomes the caption; a leading `Figure N:` is bolded and makes "Figure N" in the text a link. No `"` inside the caption. |
| Figure attributes | `![alt](assets/figures/x.png "Figure 3: …"){width=480px loading=lazy}` | Space-separated `key=value` HTML attributes, no spaces inside values; `id=…` sets the anchor. |
| Video | `![alt](assets/figures/x.mp4 "Figure 4: …"){width=700px freeze=2000}` | `.mp4/.webm/.ogg` become muted videos that play when fully visible and pause `freeze` ms between loops. |
| Side-by-side figures | `<div class="md-figgrid-2x2"><figure><img src="assets/figures/a.png" alt=""><figcaption>(a) …</figcaption></figure> … </div>` | Two columns (one below 800px). Two figures = a row; four = 2x2. Captions here are plain HTML. |
| Placeholder figure | `![alt](__IMAGE_PLACEHOLDER__ "…")` | Renders `[Image: alt]` in grey; the only missing image the build tolerates. |
| Footnote / sidenote | `text[^key]` and, on its own line anywhere, `[^key]: Author et al. (2025). [Title](https://…).` | Numbered by first use. Continuation lines need 2+ leading spaces. Shown in the right margin on wide screens, as a "Notes" list at the end on narrow ones. |
| Coloured text | `::blue[text, **bold**, $x$]::` | Colours: `gray brown orange yellow green blue purple pink red`. No `]` inside. |
| Callout | `:::callout_begin type="tip" title="Optional title":::` … `:::callout_end:::` | Types: `note` (default), `info`, `tip`, `warning`, `takeaway`. `type` must come before `title`. |
| Takeaway box | `:::takeaway_begin:::` … `:::takeaway_end:::` | Same as `callout_begin type="takeaway"`. |
| Fold (toggle) | `:::fold_begin title="Experimental setup":::` … `:::fold_end:::` | Starts closed; add `open` after the title to start open: `:::fold_begin title="…" open:::`. |
| Small print | `:::small_begin:::` … `:::small_end:::` | Tighter line height (see LAYOUT_NOTES: not actually smaller). |
| Jump link box | `:::jumpbox id="3-math" label="Go to the math section":::` | Full-width link box to `#id`. |
| Iframe embed | `<iframe src="case-studies/x.html" data-autoheight loading="lazy" title="…" style="width:100%;height:600px;border:1px solid #e5e5e5;border-radius:6px"></iframe>` | Raw HTML block; put blank lines around it. `data-autoheight` fits a same-origin page to its content after it loads. Add a normal link to open it full-page. |

Rules that apply to all `:::…:::` boxes: the markers can be inline or on their
own lines (own lines are clearer); attribute values cannot contain `"`; boxes
**cannot be nested** (a fold inside a callout shows its markers as text);
`##`/`###` inside a box render as plain headings. A takeaway (or any callout
whose title contains "takeaway") inside a `###` subsection ends that subsection:
what follows it renders at the `##` level. Markers, `##`/`###` lines and
`[^key]` inside fenced code blocks or inline code are left alone.

## Helper scripts

From the original template, for cleaning up Markdown exported from Notion:

- `scripts/figure_captions_to_image_titles.py`: moves a `Figure N: …` paragraph
  under an image into that image's title (caption).
- `scripts/external_links_to_references.py`: turns inline external links into
  `[^id]` footnotes with definitions appended.

Run each with `--help` first; they rewrite files in place or alongside.

## Deploy

**Option A: GitHub Actions (recommended).** `.github/workflows/deploy.yml`
builds with `BASE_PATH=/<repository name>` (here `/RIME`) and publishes
`build/` on every push to `main`. One-time setup: the repo must be public (on
the Free plan, Pages needs a public repo), and Settings → Pages → Source must be
set to "GitHub Actions". Pushing a workflow file with the `gh` CLI needs the
`workflow` token scope (`gh auth refresh -h github.com -s workflow`).

**Option B: publish from a folder, without Actions.** Run `npm run build:docs`
(builds into `docs/` with `BASE_PATH=/RIME`), commit `docs/`, and set
Settings → Pages → Source to "Deploy from a branch", `main`, `/docs`.
`static/.nojekyll` is copied into the output so Jekyll does not drop `_app/`.
Rebuild and commit `docs/` after every content change.

If the repo is renamed, the URL path changes with it: option A follows
automatically; for option B, edit `build:docs` in `package.json`.

## Credits

The site code is adapted, with permission, from our lab-mates' SvelteKit blog
template (compute-optimal-rl-llm-scaling.github.io), whose design descends from
[ekzhang.github.io](https://github.com/ekzhang/ekzhang.github.io). KaTeX,
marked, SvelteKit and Tailwind are MIT-licensed.
