"""Post-process the Markdown produced by convert.py (Notion -> template dialect).

1. Tables whose rows carry Notion background colours (e.g. Table 1) become raw HTML
   tables with `<tr class="nbg-<colour>">`, styled in Markdown.svelte, because GFM
   tables cannot colour rows. Other tables stay GFM.
2. Short bold run-in labels at the start of a paragraph or list item ("**Setup.**",
   "***Symbolic Alchemy.***", "**1)**") get class `md-runin`, so they stay black while
   other bold text in running prose is coloured (Markdown.svelte).
3. `####` headings become `###` (foldable, listed in the TOC).

Usage: python3 postprocess.py <notion page.txt> <converted post.md> <output post.md>
"""
import html
import re
import sys

page_txt, post_in, post_out = sys.argv[1:4]
page = open(page_txt).read()
post = open(post_in).read()

# --- 1. row colours, in table order, from the Notion source -------------------------
notion_tables = []
for m in re.finditer(r'<table[^>]*>(.*?)</table>', page, re.S):
    rows = re.findall(r'<tr([^>]*)>', m.group(1))
    notion_tables.append([(re.search(r'color="([a-z]+)_bg"', a) or [None, None])[1] for a in rows])


def inline(cell: str) -> str:
    s = html.escape(cell.strip(), quote=False)
    s = s.replace('\\*', '\x00').replace('\\|', '|')
    s = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    return s.replace('\x00', '*')


def split_row(line: str) -> list[str]:
    return re.split(r'(?<!\\)\|', line.strip().strip('|'))


lines = post.split('\n')
out, i, t = [], 0, 0
while i < len(lines):
    if lines[i].startswith('|') and i + 1 < len(lines) and re.match(r'^\|\s*:?-{3,}', lines[i + 1]):
        j = i
        while j < len(lines) and lines[j].startswith('|'):
            j += 1
        block = lines[i:j]
        colours = notion_tables[t] if t < len(notion_tables) else []
        t += 1
        body = [block[0]] + block[2:]
        if any(colours) and len(colours) == len(body):
            h = ['<table>', '<thead>']
            for k, row in enumerate(body):
                cls = f' class="nbg-{colours[k]}"' if colours[k] else ''
                tag = 'th' if k == 0 else 'td'
                cells = ''.join(f'<{tag}>{inline(c)}</{tag}>' for c in split_row(row))
                h.append(f'<tr{cls}>{cells}</tr>')
                if k == 0:
                    h += ['</thead>', '<tbody>']
            h += ['</tbody>', '</table>']
            out += h
        else:
            if any(colours):
                print(f'WARNING: table {t}: {len(colours)} Notion rows vs {len(body)} Markdown rows; left as GFM')
            out += block
        i = j
        continue
    out.append(lines[i])
    i += 1
post = '\n'.join(out)
print(f'tables: {t} in Markdown, {len(notion_tables)} in Notion; coloured -> HTML: '
      f'{sum(1 for c in notion_tables[:t] if any(c))}')

# --- 2. run-in labels -----------------------------------------------------------------
LABEL = r'[^*\n]{1,40}?[.:)]'


def runin(m):
    stars, text = m.group(2), m.group(3)
    if len(text.split()) > 4:
        return m.group(0)
    inner = f'<em>{text}</em>' if stars == '***' else text
    return f'{m.group(1)}<strong class="md-runin">{inner}</strong>'


post, n = re.subn(rf'(?m)^(\s*(?:[-*] )?)(\*\*\*|\*\*)({LABEL})\2', runin, post)
print('run-in labels marked:', n)

# --- 2b. passages to highlight (scripts/notion/highlight.txt) ---------------------------
import os
hl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'highlight.txt')
if os.path.exists(hl_path):
    for passage in (l.strip() for l in open(hl_path)):
        if not passage or passage.startswith('#'):
            continue
        # match the passage even if Notion bolded only part of it (** markers anywhere)
        words = [re.escape(w) for w in passage.split()]
        pat = r'(?:\*\*)?' + r'(?:\*\*)?\s+(?:\*\*)?'.join(words) + r'(?:\*\*)?'
        m = re.search(pat, post)
        if not m:
            print('WARNING: highlight passage not found:', passage[:60])
            continue
        post = post[:m.start()] + '**' + m.group(0).replace('**', '') + '**' + post[m.end():]
        print('highlighted:', passage[:60])

# --- 2b'. bold that stays black (scripts/notion/plain.txt) -----------------------------
# A plain line names a passage, exactly as it is bolded in Notion, that keeps the normal ink
# colour. A line "[section] <start of an H2 title>" keeps every paragraph-opening bold sentence in
# that section black.
pl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plain.txt')


def plain(text, em=False):
    return f'<strong class="md-plain">{"<em>" + text + "</em>" if em else text}</strong>'


if os.path.exists(pl_path):
    for line in (l.strip() for l in open(pl_path)):
        if not line or line.startswith('#'):
            continue
        if line.startswith('[section]'):
            title = line[len('[section]'):].strip()
            lines = post.split('\n')
            inside, n = False, 0
            for k, ln in enumerate(lines):
                if ln.startswith('## '):
                    inside = ln[3:].replace('*', '').strip().startswith(title)
                    continue
                if inside:
                    new_ln, c = re.subn(r'^(\s*(?:[-*] )?)(\*\*\*|\*\*)([^*\n]+?)\2',
                                        lambda m: m.group(1) + plain(m.group(3), m.group(2) == '***'), ln)
                    lines[k], n = new_ln, n + c
            post = '\n'.join(lines)
            print(f'plain paragraph openings in "{title}":', n)
            continue
        for stars in ('***', '**'):
            bold = stars + line + stars
            if bold in post:
                post = post.replace(bold, plain(line, stars == '***'), 1)
                print('plain bold:', line[:60])
                break
        else:
            print('WARNING: plain-bold passage not found:', line[:60])

# --- 2c. case-study iframes size themselves to their content ---------------------------
post, n = re.subn(r'<iframe src="(case-studies/[^"]+)" loading="lazy" style="width:100%;height:720px;',
                  r'<iframe src="\1" data-autoheight loading="lazy" style="width:100%;height:720px;', post)
print('auto-height iframes:', n)

# --- 3. headings ----------------------------------------------------------------------
post, n = re.subn(r'(?m)^#### ', '### ', post)
print('#### -> ###:', n)
open(post_out, 'w').write(post)
