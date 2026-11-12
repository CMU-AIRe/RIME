#!/usr/bin/env python3
"""
Convert figure-caption paragraphs in markdown into image titles so the renderer can style them.

This repo's `src/lib/components/Markdown.svelte` renders image `title` as a caption block
with smaller gray, left-aligned, full-width styling (via `.md-figcaption ... text-sm`).

What this script does:
  - Finds markdown image lines: ![alt](url)
  - If the next non-empty line is a caption paragraph like:
        Figure 2: ...
        **Figure 2:** ...
        **Figure 2: ...**
    then it moves that caption into the image title:
        ![alt](url "Figure 2: ...")
    and removes the caption paragraph.

Notes:
  - Skips fenced code blocks.
  - Leaves images that already have an explicit title unchanged.
  - If a "caption line" appears to contain additional prose (e.g., "Beyond ..."),
    it keeps the remainder as a normal paragraph after the image.
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


FENCE_RE = re.compile(r"^\s*```")

# Basic markdown image: ![alt](url "optional title"){optional attrs}
# We keep this conservative and line-based on purpose.
IMG_RE = re.compile(
    r"""^
        (?P<prefix>\s*)!
        \[(?P<alt>[^\]]*)\]
        \(
          (?P<url>[^)\s]+)
          (?P<title>\s+(?P<q>["'])(?P<title_text>.*?)(?P=q))?
        \)
        (?P<attrs>\{[^}]*\})?
        \s*$
    """,
    re.VERBOSE,
)

# Caption line patterns we accept (as a whole paragraph line).
# Examples:
#   Figure 2: ...
#   **Figure 2:** ...
#   **Figure 2: ...**
#   Figure 12(a): ...
CAPTION_RE = re.compile(
    r"""^\s*
        (?P<bold>\*\*)?
        Figure\s+
        (?P<num>\d+(?:\([a-z]\))?)
        \s*[:\.]\s*
        (?P<body>.+?)
        (?P=bold)?
        \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

SPLIT_REMAINDER_RE = re.compile(r"^(?P<cap>.*?\.)\s+(?P<rest>(Beyond|We|In|This)\b.*)$")


def _clean_caption_text(raw: str) -> str:
    s = raw.strip()
    # Strip surrounding **...** if the whole line was bolded.
    if s.startswith("**") and s.endswith("**") and len(s) >= 4:
        s = s[2:-2].strip()
    # Strip a bolded "Figure N" prefix like **Figure 2:** ...
    s = re.sub(r"^\*\*Figure\s+", "Figure ", s, flags=re.IGNORECASE)
    s = re.sub(r"\*\*$", "", s).strip()
    # Remove any leftover bold markers that commonly leak in from source markdown.
    # (We prefer captions to be plain; styling is handled by CSS.)
    s = s.replace("**", "").replace("__", "")

    # Normalize multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _quote_title(title: str) -> str:
    # Use double quotes and HTML-escape any embedded quotes to avoid breaking markdown parsing.
    # Marked will render &quot; as ".
    safe = title.replace('"', "&quot;")
    return f' "{safe}"'


@dataclass
class EditStats:
    files_changed: int = 0
    images_titled: int = 0
    captions_removed: int = 0
    captions_split: int = 0


def process_markdown_text(text: str) -> Tuple[str, EditStats]:
    lines = text.splitlines()
    out: List[str] = []
    stats = EditStats()

    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]

        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue

        if in_fence:
            out.append(line)
            i += 1
            continue

        m = IMG_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue

        # Image line found
        prefix = m.group("prefix") or ""
        alt = m.group("alt") or ""
        url = m.group("url")
        has_title = bool(m.group("title"))
        attrs = m.group("attrs") or ""
        title_text = m.group("title_text") if has_title else None

        # Look ahead for caption line
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j >= len(lines):
            out.append(line)
            i += 1
            continue

        cap_line = lines[j]
        cm = CAPTION_RE.match(cap_line)
        if not cm:
            out.append(line)
            i += 1
            continue

        # Build caption text
        # Reconstruct "Figure N: body" in a normalized way
        fig_num = cm.group("num")
        body = cm.group("body").strip()
        caption_raw = f"Figure {fig_num}: {body}"
        caption = _clean_caption_text(caption_raw)

        remainder: Optional[str] = None
        split_m = SPLIT_REMAINDER_RE.match(caption)
        if split_m:
            caption = split_m.group("cap").strip()
            remainder = split_m.group("rest").strip()
            stats.captions_split += 1

        # If image already has a title, do not overwrite it; just remove the duplicate caption line.
        if has_title:
            out.append(line)
        else:
            new_line = f"{prefix}![{alt}]({url}{_quote_title(caption)}){attrs}"
            out.append(new_line)
            stats.images_titled += 1

        # Keep original blank lines between image and caption? We remove the caption paragraph itself.
        stats.captions_removed += 1

        # Copy intervening blank lines between i and j, but ensure at most one blank line.
        # (keeps markdown structure tidy)
        if j > i + 1:
            out.append("")

        # If we split remainder prose, keep it as its own paragraph after a blank line.
        if remainder:
            out.append(remainder)

        i = j + 1

    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    return new_text, stats


def iter_md_files(target: Path) -> Iterable[Path]:
    if target.is_file():
        yield target
        return
    for p in target.rglob("*.md"):
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="Markdown file or directory to process")
    ap.add_argument("--in-place", action="store_true", help="Rewrite files in place")
    ap.add_argument("--dry-run", action="store_true", help="Print a short summary only (default)")
    ap.add_argument(
        "--normalize-asset-paths",
        action="store_true",
        help='Prefix markdown image urls like "assets/..." with "/assets/..."',
    )
    ap.add_argument(
        "--normalize-existing-titles",
        action="store_true",
        help="Clean up existing image titles (e.g., strip leftover ** markers)",
    )
    args = ap.parse_args()

    target = Path(args.target)
    if not target.exists():
        raise SystemExit(f"Target not found: {target}")

    in_place = bool(args.in_place)
    dry_run = bool(args.dry_run) or not in_place

    total = EditStats()
    changed_files: List[Path] = []

    def process_with_normalization(text: str) -> Tuple[str, EditStats]:
        new_text, stats = process_markdown_text(text)
        if not (args.normalize_asset_paths or args.normalize_existing_titles):
            return new_text, stats

        lines = new_text.splitlines()
        out2: List[str] = []
        in_fence = False
        for ln in lines:
            if FENCE_RE.match(ln):
                in_fence = not in_fence
                out2.append(ln)
                continue
            if in_fence:
                out2.append(ln)
                continue

            m = IMG_RE.match(ln)
            if not m:
                out2.append(ln)
                continue

            prefix = m.group("prefix") or ""
            alt = m.group("alt") or ""
            url = m.group("url")
            attrs = m.group("attrs") or ""
            has_title = bool(m.group("title"))
            title_text = m.group("title_text") if has_title else None

            if args.normalize_asset_paths and url.startswith("assets/"):
                url = "/" + url

            if args.normalize_existing_titles and title_text is not None:
                title_text = _clean_caption_text(title_text)

            if has_title and title_text is not None:
                out2.append(f"{prefix}![{alt}]({url}{_quote_title(title_text)}){attrs}")
            else:
                out2.append(f"{prefix}![{alt}]({url}){attrs}")

        out_final = "\n".join(out2) + ("\n" if new_text.endswith("\n") else "")
        return out_final, stats

    for md_path in iter_md_files(target):
        old = md_path.read_text(encoding="utf-8")
        new, stats = process_with_normalization(old)
        if new != old:
            changed_files.append(md_path)
            total.files_changed += 1
            total.images_titled += stats.images_titled
            total.captions_removed += stats.captions_removed
            total.captions_split += stats.captions_split
            if in_place:
                md_path.write_text(new, encoding="utf-8")

    print(f"files_changed={total.files_changed}")
    print(f"images_titled={total.images_titled}")
    print(f"captions_removed={total.captions_removed}")
    print(f"captions_split={total.captions_split}")
    if dry_run and changed_files:
        # Keep this short to avoid noisy output.
        print("example_changed_file=", str(changed_files[0]))
        if len(changed_files) > 1:
            print(f"... and {len(changed_files) - 1} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


