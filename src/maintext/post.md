This page is a **layout and syntax showcase** with placeholder text. Every demo shows the Markdown source in a grey code block, followed by what it renders to. The title block above comes from `src/maintext/meta.json`, not from this file. Text placed before the first `##` heading (like this paragraph) sits outside any collapsible section.

:::jumpbox id="7-boxes-callouts-folds" label="Jump straight to the boxes, callouts and folds (a jumpbox demo)":::

## 1. Headings and sections

```markdown
## 1. Headings and sections        <- level 2: a collapsible section (starts open)
### 1.1 A level-3 subsection       <- level 3: nested collapsible (starts open)
#### A level-4 heading             <- plain heading, not collapsible, not in the TOC
```

Every `##` heading wraps everything up to the next `##` in a collapsible section; click the heading (or its caret) to fold it. Every `###` does the same inside its `##`. Both start **open**. `##` and `###` headings also appear in the fixed table of contents on the left on wide screens. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

### 1.1 A level-3 subsection

Body text of a `###` subsection is indented one more step than `##` body text. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

#### A level-4 heading

A `####` heading is an ordinary heading inside the current section: no fold, no TOC entry. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.

### 1.2 Another level-3 subsection

Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

## 2. Text, links, colour, footnotes

```markdown
Plain text with **bold**, *italic*, ***bold italic***, ~~strikethrough~~ and `inline code`.
An [external link](https://example.com), an [in-page link](#3-math), and a footnote.[^demo-note]
```

Plain text with **bold**, *italic*, ***bold italic***, ~~strikethrough~~ and `inline code`.
An [external link](https://example.com), an [in-page link](#3-math), and a footnote.[^demo-note]

```markdown
A citation-style footnote[^cite-a] and a second, longer one.[^cite-b]

[^cite-a]: Author et al. (2025). [A Paper Title](https://example.com/paper).
[^cite-b]: Footnote text can span lines when continuation lines
  are indented by two or more spaces. It may contain *Markdown* and $x^2$.
```

A citation-style footnote[^cite-a] and a second, longer one.[^cite-b] Footnotes are numbered by first use, wherever their definitions sit in the file. On wide screens they appear as sidenotes in the right margin, level with the line that cites them; on narrow screens they become a numbered "Notes" list after the article.

```markdown
::gray[gray]:: ::brown[brown]:: ::orange[orange]:: ::yellow[yellow]:: ::green[green]::
::blue[blue]:: ::purple[purple]:: ::pink[pink]:: ::red[red]:: and ::blue[**bold blue with $\alpha$**]::
```

::gray[gray]:: ::brown[brown]:: ::orange[orange]:: ::yellow[yellow]:: ::green[green]::
::blue[blue]:: ::purple[purple]:: ::pink[pink]:: ::red[red]:: and ::blue[**bold blue with $\alpha$**]::

```markdown
> A blockquote. It is rendered as a grey inline box with a dark left border,
> sized to its content.
```

> A blockquote. It is rendered as a grey inline box with a dark left border,
> sized to its content.

```markdown
- Unordered item
  - Nested item
1. Ordered item
2. Second ordered item
- [x] Task list item (GFM)
- [ ] Unchecked task
```

- Unordered item
  - Nested item
- Another unordered item

1. Ordered item
2. Second ordered item

- [x] Task list item (GFM)
- [ ] Unchecked task

A horizontal rule is `---` on its own line, with blank lines around it:

---

## 3. Math

```markdown
Inline math such as $f_\theta(x) = \sigma(Wx + b)$ stays on one line. A literal dollar sign is written \$5.
```

Inline math such as $f_\theta(x) = \sigma(Wx + b)$ stays on one line. A literal dollar sign is written \$5.

```markdown
$$
\mathcal{L}(\theta) = \mathbb{E}_{(x, y) \sim \mathcal{D}} \big[ -\log p_\theta(y \mid x) \big]
$$
```

$$
\mathcal{L}(\theta) = \mathbb{E}_{(x, y) \sim \mathcal{D}} \big[ -\log p_\theta(y \mid x) \big]
$$

```markdown
$$
\begin{aligned}
m_{t+1} &= \operatorname{Write}(m_t, \tau_t) \\
a_t &\sim \pi_\theta(\cdot \mid s_t, m_t) \\
J(\theta) &= \sum_{t=1}^{T} \gamma^{t} \, r_t
\end{aligned}
$$
```

$$
\begin{aligned}
m_{t+1} &= \operatorname{Write}(m_t, \tau_t) \\
a_t &\sim \pi_\theta(\cdot \mid s_t, m_t) \\
J(\theta) &= \sum_{t=1}^{T} \gamma^{t} \, r_t
\end{aligned}
$$

A long display equation scrolls sideways inside its own box instead of widening the page:

$$
R_{\text{total}} = r_1 + \gamma r_2 + \gamma^2 r_3 + \gamma^3 r_4 + \gamma^4 r_5 + \gamma^5 r_6 + \gamma^6 r_7 + \gamma^7 r_8 + \gamma^8 r_9 + \gamma^9 r_{10} + \gamma^{10} r_{11} + \gamma^{11} r_{12} + \cdots
$$

A KaTeX error is shown in red instead of failing the build: $\notacommand{x}$.

## 4. Figures

```markdown
![Basic figure](assets/figures/demo-basic.png "Figure 1: A caption comes from the image title. It may contain *Markdown* and math $\beta$.")
```

![Basic figure](assets/figures/demo-basic.png "Figure 1: A caption comes from the image title. It may contain *Markdown* and math $\beta$.")

```markdown
![Narrow figure](assets/figures/demo-basic.png "Figure 2: The {...} suffix adds HTML attributes, here a 420px width."){width=420px loading=lazy}
```

![Narrow figure](assets/figures/demo-basic.png "Figure 2: The {...} suffix adds HTML attributes, here a 420px width."){width=420px loading=lazy}

A tall image should be given a width, or it will fill the column and take a whole screen:

```markdown
![Tall figure](assets/figures/demo-tall.png "Figure 3: A tall (portrait) figure limited to 300px wide."){width=300px loading=lazy}
```

![Tall figure](assets/figures/demo-tall.png "Figure 3: A tall (portrait) figure limited to 300px wide."){width=300px loading=lazy}

A wide image never overflows; it is scaled down to the text column (there is no full-bleed mode):

```markdown
![Wide figure](assets/figures/demo-wide.png "Figure 4: A 1600x500 image, scaled to the column width."){loading=lazy}
```

![Wide figure](assets/figures/demo-wide.png "Figure 4: A 1600x500 image, scaled to the column width."){loading=lazy}

An animated GIF uses the same syntax:

```markdown
![Animated GIF](assets/figures/demo-anim.gif "Figure 5: GIFs animate natively."){width=480px loading=lazy}
```

![Animated GIF](assets/figures/demo-anim.gif "Figure 5: GIFs animate natively."){width=480px loading=lazy}

Plain-text references such as Figure 1 or Fig. 4 become links to the figure whose caption starts with that number (in the browser, after the page loads).

Side by side, use the raw-HTML grid. It has two columns on wide screens and one column below 800px. Paths inside raw HTML follow the same rule as Markdown paths.

```markdown
<div class="md-figgrid-2x2">
  <figure><img src="assets/figures/demo-grid-a.png" alt="Panel a"><figcaption>(a) First panel.</figcaption></figure>
  <figure><img src="assets/figures/demo-grid-b.png" alt="Panel b"><figcaption>(b) Second panel.</figcaption></figure>
</div>
```

<div class="md-figgrid-2x2">
  <figure><img src="assets/figures/demo-grid-a.png" alt="Panel a" loading="lazy"><figcaption>(a) First panel.</figcaption></figure>
  <figure><img src="assets/figures/demo-grid-b.png" alt="Panel b" loading="lazy"><figcaption>(b) Second panel.</figcaption></figure>
</div>

Four `<figure>`s in the same grid make a 2x2 block. A root-absolute path (`/assets/...`) also works; the base path is added automatically:

<div class="md-figgrid-2x2">
  <figure><img src="/assets/figures/demo-grid-a.png" alt="Panel a2" loading="lazy"><figcaption>(a) Root-absolute src.</figcaption></figure>
  <figure><img src="/assets/figures/demo-grid-b.png" alt="Panel b2" loading="lazy"><figcaption>(b) Root-absolute src.</figcaption></figure>
  <figure><img src="assets/figures/demo-grid-c.png" alt="Panel c" loading="lazy"><figcaption>(c) Relative src.</figcaption></figure>
  <figure><img src="assets/figures/demo-grid-d.png" alt="Panel d" loading="lazy"><figcaption>(d) Relative src.</figcaption></figure>
</div>

```markdown
![Figure not ready yet](__IMAGE_PLACEHOLDER__ "Figure 6: shown as a grey placeholder line")
```

![Figure not ready yet](__IMAGE_PLACEHOLDER__ "Figure 6: shown as a grey placeholder line")

## 5. Tables

```markdown
| Method | Score | Notes |
|:-------|------:|:------|
| Baseline | 0.41 | no memory |
| Ours | **0.57** | with $m_t$ |
```

| Method | Score | Notes |
|:-------|------:|:------|
| Baseline | 0.41 | no memory |
| Ours | **0.57** | with $m_t$ |

A wide table scrolls sideways inside its own box (header cells never wrap):

| Setting | Model | Steps | Batch | LR | Seq len | Memory | Eval 1 | Eval 2 | Eval 3 | Eval 4 | Mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | placeholder-7B | 400 | 64 | 1e-6 | 20480 | on | 0.31 | 0.29 | 0.35 | 0.33 | 0.32 |
| B | placeholder-7B | 400 | 64 | 1e-6 | 20480 | off | 0.22 | 0.24 | 0.21 | 0.26 | 0.23 |

## 6. Code

````markdown
```python
import re
...
```
````

```python
import re

## A line starting with "##" inside a code block is NOT a section heading.
def clean(text: str) -> str:
    # The regex below is NOT turned into a footnote reference, and $x$ is not math.
    return re.sub(r"[^a-z0-9]+", "-", text.lower())
```

Code blocks scroll sideways when long and get a "Copy" button in the browser.

## 7. Boxes, callouts, folds

```markdown
:::callout_begin type="note":::
A **note** callout (the default type). The label defaults to the type name.
:::callout_end:::
```

:::callout_begin type="note":::
A **note** callout (the default type). The label defaults to the type name.
:::callout_end:::

:::callout_begin type="info":::
`type="info"`: note that its default label is "Takeaways" (template quirk). Give it a `title` to change that.
:::callout_end:::

:::callout_begin type="info" title="Info with a custom title":::
`type="info" title="..."`. The `type` attribute must come before `title`.
:::callout_end:::

:::callout_begin type="tip":::
`type="tip"`: green.
:::callout_end:::

:::callout_begin type="warning":::
`type="warning"`: amber.
:::callout_end:::

:::callout_begin type="takeaway" title="Key result":::
`type="takeaway"`: the brown box. Inside a `###` subsection a takeaway ends that subsection (see 7.2).
:::callout_end:::

```markdown
:::takeaway_begin:::
Shorthand for a takeaway callout with the default "Takeaways" label.
:::takeaway_end:::
```

:::takeaway_begin:::
Shorthand for a takeaway callout with the default "Takeaways" label.
:::takeaway_end:::

```markdown
:::small_begin:::
Small print: the same Markdown in a smaller font size.
:::small_end:::
```

:::small_begin:::
Small print: the same Markdown in a smaller font size. Useful for setup details or long caveats. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.
:::small_end:::

```markdown
:::fold_begin title="Experimental setup (starts closed)":::
Hidden until the reader clicks. Any Markdown works here, but no nested boxes.
:::fold_end:::
```

:::fold_begin title="Experimental setup (starts closed)":::
Hidden until the reader clicks. Any Markdown works here (lists, math $\lambda$, tables, images), but no nested folds or callouts.

- Placeholder detail one
- Placeholder detail two
:::fold_end:::

```markdown
:::fold_begin title="A fold that starts open" open:::
Add the word open after the title.
:::fold_end:::
```

:::fold_begin title="A fold that starts open" open:::
Add the word `open` after the title.
:::fold_end:::

```markdown
:::jumpbox id="3-math" label="Back to the math section":::
```

:::jumpbox id="3-math" label="Back to the math section":::

### 7.1 Ordinary subsection

Text inside a `###` subsection. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.

### 7.2 Subsection followed by a takeaway

This paragraph belongs to subsection 7.2.

:::takeaway_begin:::
A takeaway inside a `###` subsection closes that subsection: the takeaway and anything after it (until the next `###`) render at the `##` level, with less indentation.
:::takeaway_end:::

This paragraph comes after the takeaway, so it is no longer inside 7.2's fold.

## 8. Embeds and raw HTML

```markdown
<iframe src="case-studies/demo.html" data-autoheight loading="lazy" title="Demo case study"
  style="width:100%;height:360px;border:1px solid #e5e5e5;border-radius:6px"></iframe>

[Open the case study in a new tab](case-studies/demo.html)
```

<iframe src="case-studies/demo.html" data-autoheight loading="lazy" title="Demo case study" style="width:100%;height:360px;border:1px solid #e5e5e5;border-radius:6px"></iframe>

[Open the case study in a new tab](case-studies/demo.html)

Files in `static/` are served as-is at the same relative path. `data-autoheight` resizes a same-origin iframe to its content once it loads; `height` is the fallback.

Other raw HTML passes straight through, e.g. <kbd>Ctrl</kbd>+<kbd>C</kbd> or <span style="background:#fef3c7">an inline highlight</span>.

[^demo-note]: A footnote definition is a line `[^id]: text`. It can sit anywhere in the file and is removed from the body.
[^cite-a]: Author et al. (2025). [A Paper Title](https://example.com/paper).
[^cite-b]: Footnote text can span lines when continuation lines
  are indented by two or more spaces. It may contain *Markdown* and $x^2$.
