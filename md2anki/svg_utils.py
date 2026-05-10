"""Programmatic SVG generation for Anki card diagrams.

Keeps SVG assets out of Python code — call these functions to produce
inline SVG markup for embedding in card fields.
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape as xmlescape


# ── Helpers ─────────────────────────────────────────────────────────────

def _color(r: int, g: int, b: int, a: float = 1.0) -> str:
    if a < 1.0:
        return f"rgba({r},{g},{b},{a})"
    return f"rgb({r},{g},{b})"


def _style(props: dict[str, str]) -> str:
    return "; ".join(f"{k}: {v}" for k, v in props.items())


# ── Venn / Euler diagrams ───────────────────────────────────────────────

def venn(
    sets: list[dict],
    *,
    width: int = 320,
    height: int = 240,
) -> str:
    """Draw a 2‑set or 3‑set Venn diagram.

    Each entry in *sets*:
      ``{"label": "A", "fill": "#2D7DD2", "opacity": 0.25}``

    Returns an inline SVG string.
    """
    if not sets:
        return ""
    n = len(sets)
    cx, cy = width // 2, height // 2
    r = min(width, height) * 0.30

    if n == 2:
        offset = r * 0.35
        circles = [
            (cx - offset, cy, r),
            (cx + offset, cy, r),
        ]
    else:
        # 3 circles in a triangle arrangement
        d = r * 0.55
        circles = [
            (cx, cy - d, r),           # top
            (cx - d * 0.87, cy + d * 0.5, r),  # bottom-left
            (cx + d * 0.87, cy + d * 0.5, r),  # bottom-right
        ]

    parts: list[str] = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    ]

    for i, (x, y, rr) in enumerate(circles):
        s = sets[i] if i < len(sets) else {}
        fill = s.get("fill", "#2D7DD2")
        opacity = s.get("opacity", 0.2)
        parts.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" '
            f'fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{fill}" stroke-width="2"/>'
        )

    # Labels
    for i, (x, y, rr) in enumerate(circles):
        s = sets[i] if i < len(sets) else {}
        label = xmlescape(s.get("label", chr(65 + i)))
        # place label near the "far" edge of each circle
        angle = -math.pi / 2 + (i * 2 * math.pi / n) if n == 3 else (
            -math.pi / 2 if i == 0 else math.pi / 2
        )
        lx = x + (rr * 0.65) * math.cos(angle)
        ly = y + (rr * 0.65) * math.sin(angle)
        parts.append(
            f'<text x="{lx:.0f}" y="{ly:.0f}" '
            f'fill="#E0E0E0" font-size="16" '
            f'text-anchor="middle" dominant-baseline="central">{label}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


# ── Animated math steps ─────────────────────────────────────────────────

def animated_steps(
    steps: list[str],
    *,
    width: int = 400,
    height: int | None = None,
) -> str:
    """Generate an SVG that reveals math derivation steps one by one via CSS.

    Each step fades in 0.4 s after the previous step.
    """
    n = len(steps)
    h = height or max(120, n * 60 + 40)
    parts: list[str] = [
        f'<svg width="{width}" height="{h}" '
        f'viewBox="0 0 {width} {h}" xmlns="http://www.w3.org/2000/svg">',
        '<style>',
        '  .step { opacity: 0; animation: fadeStep 0.4s ease forwards; }',
        '  @keyframes fadeStep { to { opacity: 1; } }',
    ]
    for i in range(n):
        delay = i * 0.4
        parts.append(f'  .s{i} {{ animation-delay: {delay}s; }}')
    parts.append("</style>")

    for i, text in enumerate(steps):
        y = 30 + i * 50
        escaped = xmlescape(text)
        is_last = (i == n - 1)
        color = "#F77F00" if is_last else "#E0E0E0"
        parts.append(
            f'<text x="20" y="{y}" class="step s{i}" '
            f'fill="{color}" font-size="16" '
            f'font-family="SF Mono, monospace">{escaped}</text>'
        )
        if not is_last and i + 1 < n:
            parts.append(
                f'<line x1="20" y1="{y + 8}" x2="20" y2="{y + 38}" '
                f'stroke="#555" stroke-width="1" class="step s{i}"/>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


# ── Simple flow chart ───────────────────────────────────────────────────

def flow_chart(
    nodes: list[dict],
    edges: list[tuple[int, int]],
    *,
    width: int = 400,
    height: int = 300,
) -> str:
    """Build a simple flowchart SVG.

    *nodes*: ``[{"label": "Start", "x": 50, "y": 20}, ...]``
    *edges*: ``[(from_index, to_index), ...]``
    """
    parts: list[str] = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
    ]

    for fi, ti in edges:
        if fi >= len(nodes) or ti >= len(nodes):
            continue
        f, t = nodes[fi], nodes[ti]
        parts.append(
            f'<line x1="{f["x"]}" y1="{f["y"] + 24}" '
            f'x2="{t["x"]}" y2="{t["y"] - 4}" '
            f'stroke="#555" stroke-width="1.5" '
            f'marker-end="url(#arrow)"/>'
        )

    parts.append(
        '<defs><marker id="arrow" viewBox="0 0 8 8" '
        'refX="6" refY="4" markerWidth="6" markerHeight="6" orient="auto">'
        '<path d="M 0 0 L 8 4 L 0 8 z" fill="#555"/></marker></defs>'
    )

    for node in nodes:
        x, y = node["x"], node["y"]
        label = xmlescape(node.get("label", ""))
        rx = node.get("rx", 8)
        parts.append(
            f'<rect x="{x}" y="{y}" width="100" height="36" rx="{rx}" '
            f'fill="rgba(45,125,210,0.12)" '
            f'stroke="#2D7DD2" stroke-width="1.5"/>'
        )
        parts.append(
            f'<text x="{x + 50}" y="{y + 22}" '
            f'fill="#E0E0E0" font-size="13" '
            f'text-anchor="middle">{label}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
