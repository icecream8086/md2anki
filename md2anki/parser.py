"""Parse Markdown files into structured sections."""

from __future__ import annotations

import re
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .models import CodeBlock, DiagramBlock, ImageRef, Section

MD = MarkdownIt("commonmark", {"maxNesting": 20})


def _is_diagram(token: Token) -> bool:
    """Check whether a fenced code block is a known diagram language."""
    info = token.info.strip().lower()
    return info in ("mermaid", "plantuml", "puml", "dot")


def parse_file(path: Path) -> list[Section]:
    """Parse a single markdown file into a list of *Section* objects."""
    text = path.read_text(encoding="utf-8")
    tokens = MD.parse(text)

    sections: list[Section] = []
    current: Section | None = None
    fence_lines_used: set[int] = set()  # avoid double-processing nested tokens

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # —— heading → new section ——
        if tok.type == "heading_open":
            level = int(tok.tag[1])  # "h1" → 1
            # next token is inline with heading text
            heading_text = ""
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                heading_text = tokens[i + 1].content.strip()
            # skip heading_close too
            i += 3 if i + 2 < len(tokens) and tokens[i + 2].type == "heading_close" else 2

            current = Section(
                heading=heading_text or "Untitled",
                heading_level=level,
                source_file=path.name,
                line_start=tok.map[0] + 1 if tok.map else 0,
            )
            sections.append(current)
            continue

        if current is None:
            # content before the first heading → create an implicit section
            current = Section(heading="(intro)", source_file=path.name)
            sections.append(current)

        # —— fenced code block ——
        if tok.type == "fence":
            info = tok.info.strip()
            lang = info.split()[0] if info else ""
            fence_lines_used.add(i)

            if _is_diagram(tok):
                kind = "plantuml" if lang.lower() in ("plantuml", "puml") else "mermaid"
                current.diagrams.append(
                    DiagramBlock(kind=kind, content=tok.content)
                )
            else:
                current.code_blocks.append(
                    CodeBlock(language=lang, content=tok.content)
                )
            i += 1
            continue

        # —— inline images (gather from inline tokens) ——
        if tok.type == "inline" and "image" in MD.parseInline(tok.content, {})[0].content if False else False:
            pass  # handled below via regex

        i += 1

    # Second pass: extract images and content per section
    for tok in tokens:
        if tok.type == "inline" and tok.content:
            for m in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', tok.content):
                src = m.group(2)
                alt = m.group(1)
                if current:
                    current.images.append(ImageRef(alt_text=alt, src=src))

    # Collect plain-text content per section using heading positions as boundaries
    heading_opens = [j for j, t in enumerate(tokens) if t.type == "heading_open"]
    section_text: list[str] = [""] * len(sections)

    # Build token-index ranges for each section
    ranges: list[tuple[int, int]] = []
    if not heading_opens:
        # no headings → everything goes to section 0
        ranges = [(0, len(tokens))]
    elif heading_opens[0] > 0 and sections[0].heading == "(intro)":
        # intro section covers tokens before first heading
        ranges = [(0, heading_opens[0])]
        ranges += [
            (heading_opens[i], heading_opens[i + 1] if i + 1 < len(heading_opens) else len(tokens))
            for i in range(len(heading_opens))
        ]
    else:
        # first section corresponds to first heading
        ranges = [
            (heading_opens[i], heading_opens[i + 1] if i + 1 < len(heading_opens) else len(tokens))
            for i in range(len(heading_opens))
        ]

    for sec_idx, (start, end) in enumerate(ranges):
        if sec_idx >= len(section_text):
            break
        for j in range(start, end):
            t = tokens[j]
            if j in fence_lines_used:
                continue
            if t.type == "inline":
                section_text[sec_idx] += t.content + "\n"
            elif t.type in ("html_block", "html_inline"):
                # preserve raw HTML (e.g. <svg>…) and inline SVG
                section_text[sec_idx] += t.content + "\n"

    for sec, txt in zip(sections, section_text):
        sec.content = txt.strip()

    return sections


def parse_all(src_dir: Path) -> list[Section]:
    """Parse every ``.md`` file in *src_dir* and return a flat list of sections."""
    md_files = sorted(src_dir.glob("*.md"))
    sections: list[Section] = []
    for fpath in md_files:
        sections.extend(parse_file(fpath))
    return sections
