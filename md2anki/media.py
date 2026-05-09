"""Collect media files (images, SVGs) for the Anki package."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import config
from .models import Section


def collect_media(sections: list[Section]) -> dict[str, Path]:
    """Copy all referenced media into ``MEDIA_DIR``.

    Returns a mapping of *destination filename → source Path*.
    """
    media_dir = config.MEDIA_DIR
    media_dir.mkdir(parents=True, exist_ok=True)

    collected: dict[str, Path] = {}

    # 1. Diagram SVGs (already rendered in out/)
    for sec in sections:
        for diag in sec.diagrams:
            if diag.output_svg:
                src = config.OUT_DIR / diag.output_svg
                dst = media_dir / diag.output_svg
                if src.exists():
                    shutil.copy2(src, dst)
                    collected[diag.output_svg] = dst

    # 2. Inline images referenced in markdown
    for sec in sections:
        for img in sec.images:
            src = _resolve_image_path(img.src)
            if src and src.exists():
                fname = src.name
                dst = media_dir / fname
                # avoid re-copying same filename
                if not dst.exists():
                    shutil.copy2(src, dst)
                collected[fname] = dst

    return collected


def _resolve_image_path(src: str) -> Path | None:
    """Resolve an image reference to an absolute path."""
    p = Path(src)
    if p.is_absolute():
        return p
    # try relative to src_dir
    candidate = config.SRC_DIR / p
    if candidate.exists():
        return candidate
    # try relative to project root
    candidate = config.PROJECT_ROOT / p
    if candidate.exists():
        return candidate
    return None
