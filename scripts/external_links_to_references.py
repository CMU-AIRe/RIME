#!/usr/bin/env python3
"""
Convert external markdown links into the repo's existing footnote reference style.

This repo already supports "footnote references" in `Markdown.svelte`:
  - references in text: [^some-id]
  - definitions at end of file: [^some-id]: ... https://example.com

What this script does:
  - Finds markdown links in normal text: [label](https://...)
  - Replaces them with: label[^auto-id]
  - Appends new footnote definitions for any new external URLs.
  - Skips fenced code blocks and existing footnote definition blocks.
  - Deduplicates by URL (same URL -> same footnote id).

Notes / constraints:
  - Only treats http/https links as "external".
  - Does NOT touch image links: ![alt](...)
  - Pragmatic markdown parsing (line-based state machine); not a full parser.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
FOOTNOTE_CONT_RE = re.compile(r"^(?:\s{2,}|\t).+")

# Standard markdown links (NOT images), single-line:
# [text](https://example.com)
# [text](https://example.com "title")
MD_LINK_RE = re.compile(
    r"(?<!\!)\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)(?P<title>\s+\"[^\"]*\")?\)"
)

URL_RE = re.compile(r"https?://\S+")


def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s


def is_fence_line(line: str) -> bool:
    # minimal: treat "```" starting a line as a fence toggle
    return line.lstrip().startswith("```")


def parse_existing_footnotes(lines: List[str]) -> Tuple[Dict[str, List[str]], Set[int]]:
    """
    Return:
      - defs: id -> raw lines (without the leading [^id]: prefix stripped)
      - def_line_idxs: indices (0-based) that are part of footnote definition blocks
    """
    defs: Dict[str, List[str]] = {}
    def_line_idxs: Set[int] = set()

    current_id: Optional[str] = None
    current_lines: List[str] = []
    current_idxs: List[int] = []

    def flush():
        nonlocal current_id, current_lines, current_idxs
        if current_id is not None:
            defs[current_id] = list(current_lines)
            for ix in current_idxs:
                def_line_idxs.add(ix)
        current_id = None
        current_lines = []
        current_idxs = []

    for ix, line in enumerate(lines):
        m = FOOTNOTE_DEF_RE.match(line.rstrip("\n"))
        if m:
            flush()
            current_id = m.group(1)
            current_lines = [m.group(2)]
            current_idxs = [ix]
            continue

        if current_id is not None and (line.strip() == "" or FOOTNOTE_CONT_RE.match(line)):
            # continuation lines belong to the def block (blank line is allowed as part of block)
            current_lines.append(line.rstrip("\n"))
            current_idxs.append(ix)
            continue

        # end of a def block
        if current_id is not None:
            flush()

    flush()
    return defs, def_line_idxs


def build_url_to_id(existing_defs: Dict[str, List[str]]) -> Dict[str, str]:
    url_to_id: Dict[str, str] = {}
    for fid, raw_lines in existing_defs.items():
        joined = " ".join(raw_lines)
        m = URL_RE.search(joined)
        if not m:
            continue
        url = m.group(0).rstrip(").,;")
        # If multiple footnotes contain the same URL, keep the first id.
        url_to_id.setdefault(url, fid)
    return url_to_id


def make_id_for_url(url: str, used_ids: Set[str]) -> str:
    """
    Create a readable, stable-ish id from the URL, ensuring uniqueness.
    """
    # domain + last segment works well for arxiv/hf/etc.
    try:
        # simple parse without urllib to avoid edge-cases; good enough for our URLs
        u = url.replace("https://", "").replace("http://", "")
        domain = u.split("/", 1)[0]
        rest = u[len(domain) :].lstrip("/")
        last = rest.split("/")[-1] if rest else domain
        base = slugify(f"{domain}-{last}")[:48] or "ext"
    except Exception:
        base = "ext"

    candidate = base
    k = 2
    while candidate in used_ids:
        candidate = f"{base}-{k}"
        k += 1
    used_ids.add(candidate)
    return candidate


@dataclass
class NewFootnote:
    fid: str
    label: str
    url: str


def convert_file(path: pathlib.Path, in_place: bool) -> Tuple[bool, str]:
    """
    Returns (changed, message).
    """
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(True)

    existing_defs, def_line_idxs = parse_existing_footnotes([l.rstrip("\n") for l in lines])
    url_to_id = build_url_to_id(existing_defs)

    used_ids: Set[str] = set(existing_defs.keys())
    new_footnotes: Dict[str, NewFootnote] = {}
    new_order: List[str] = []

    out_lines: List[str] = []
    in_code = False

    for ix, line in enumerate(lines):
        if is_fence_line(line):
            in_code = not in_code
            out_lines.append(line)
            continue

        if in_code or ix in def_line_idxs:
            out_lines.append(line)
            continue

        def repl(m: re.Match[str]) -> str:
            label = m.group("label") or ""
            url = m.group("url") or ""

            # Reuse id if URL already exists.
            fid = url_to_id.get(url)
            if not fid:
                fid = make_id_for_url(url, used_ids)
                url_to_id[url] = fid
                # keep first label as description
                new_footnotes[fid] = NewFootnote(fid=fid, label=label, url=url)
                new_order.append(fid)

            # Replace inline link with text + footnote ref
            label_txt = label.strip()
            if not label_txt:
                return f"[^{fid}]"
            return f"{label_txt}[^{fid}]"

        new_line = MD_LINK_RE.sub(repl, line)
        out_lines.append(new_line)

    # Append new defs (if any)
    if new_order:
        # Ensure trailing newline and a blank line before definitions.
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines[-1] = out_lines[-1] + "\n"
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("\n")

        for fid in new_order:
            nf = new_footnotes[fid]
            desc = (nf.label or "").strip()
            if desc:
                # Ensure a period before URL for readability, matching existing style.
                if desc.endswith((".", "!", "?", ":", ";")):
                    line = f"[^{fid}]: {desc} {nf.url}\n"
                else:
                    line = f"[^{fid}]: {desc}. {nf.url}\n"
            else:
                line = f"[^{fid}]: {nf.url}\n"
            out_lines.append(line)

    out = "".join(out_lines)
    changed = out != raw

    if changed and in_place:
        path.write_text(out, encoding="utf-8")

    msg = f"{path}: {'updated' if changed else 'no changes'}; new footnotes: {len(new_order)}"
    return changed, msg


def iter_md_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*.md")):
        if p.name.startswith("."):
            continue
        yield p


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=pathlib.Path, help="Path to a .md file or a directory to process")
    ap.add_argument(
        "--in-place",
        action="store_true",
        help="Write changes back to the file(s). Without this flag, runs in dry-run mode.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of files processed (0 = no limit).",
    )
    args = ap.parse_args(argv)

    root: pathlib.Path = args.path
    if not root.exists():
        print(f"ERROR: not found: {root}", file=sys.stderr)
        return 2

    changed_any = False
    processed = 0
    for p in iter_md_files(root):
        processed += 1
        if args.limit and processed > args.limit:
            break
        changed, msg = convert_file(p, in_place=args.in_place)
        changed_any = changed_any or changed
        print(msg)

    if not args.in_place:
        print("\n(dry-run) Re-run with --in-place to apply changes.")
    return 0 if not changed_any else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


