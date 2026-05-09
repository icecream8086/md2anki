#!/usr/bin/env python3
"""md2anki — Convert Markdown notes to Anki flashcards.

Usage:
    python md2anki.py process              # Full pipeline
    python md2anki.py list-sections         # Show parsed sections
    python md2anki.py config               # Show current config
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Ensure the package directory is importable
_project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_project_root))

from md2anki import (
    anki_builder,
    card_generator,
    config,
    diagram_renderer,
    media,
    parser,
)
from md2anki.models import Deck

app = typer.Typer(help="Convert Markdown notes to Anki flashcards.")
console = Console()


@app.command()
def process(
    deck_name: str | None = typer.Option(None, "--deck", "-d", help="Anki deck name"),
    cards_per_section: int | None = typer.Option(
        None, "--cards", "-c", help="Cards per section"
    ),
    src_dir: str | None = typer.Option(
        None, "--src", "-s", help="Source markdown directory"
    ),
    model: str | None = typer.Option(
        None, "--model", "-m", help="Anthropic model name"
    ),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI generation, use placeholder cards"),
) -> None:
    """Run the full pipeline: parse → render diagrams → generate cards → build .apkg."""
    if deck_name:
        config.settings.deck_name = deck_name
    if cards_per_section:
        config.settings.cards_per_section = cards_per_section
    if src_dir:
        config.settings.src_dir = src_dir
        config.SRC_DIR = _project_root / src_dir
    if model:
        config.settings.anthropic_model = model
    if no_ai:
        config.settings.anthropic_api_key = ""

    console.print("[bold]md2anki[/bold] — Markdown to Anki converter\n")

    # 1. Parse
    console.print("[1/5] Parsing markdown files...")
    config.SRC_DIR.mkdir(parents=True, exist_ok=True)
    sections = parser.parse_all(config.SRC_DIR)
    if not sections:
        console.print("  [yellow]No sections found. Place .md files in src/[/yellow]")
        raise typer.Exit(1)
    console.print(f"  → {len(sections)} sections from {len({s.source_file for s in sections})} file(s)")

    # 2. Render diagrams
    console.print("[2/5] Rendering diagrams...")
    all_diagrams = [d for s in sections for d in s.diagrams]
    if all_diagrams:
        diagram_renderer.render_diagrams(all_diagrams, config.OUT_DIR)
        rendered = sum(1 for d in all_diagrams if d.output_svg)
        console.print(f"  → {rendered}/{len(all_diagrams)} diagrams rendered")
    else:
        console.print("  → (none found)")

    # 3. Generate cards
    console.print("[3/5] Generating flashcards...")
    cards = card_generator.generate_cards(sections) if not no_ai else card_generator._placeholder_cards(sections)
    console.print(f"  → {len(cards)} cards generated")

    if not cards:
        console.print("  [red]No cards generated — aborting.[/red]")
        raise typer.Exit(1)

    # 4. Collect media
    console.print("[4/5] Collecting media...")
    media_map = media.collect_media(sections)
    console.print(f"  → {len(media_map)} media file(s)")

    # 5. Build .apkg
    console.print("[5/5] Building Anki package...")
    deck = Deck(
        name=config.settings.deck_name,
        cards=cards,
        media_paths=list(media_map.values()),
    )
    out_path = anki_builder.build_package(deck)
    console.print(f"\n[green]✓ Done![/green] Package written to: [bold]{out_path}[/bold]")
    if media_map:
        console.print(f"  Media directory: {config.MEDIA_DIR}")


@app.command()
def list_sections(
    src_dir: str | None = typer.Option(None, "--src", "-s", help="Source directory"),
) -> None:
    """List all parsed sections from the markdown files."""
    if src_dir:
        config.SRC_DIR = _project_root / src_dir
    config.SRC_DIR.mkdir(parents=True, exist_ok=True)
    sections = parser.parse_all(config.SRC_DIR)

    if not sections:
        console.print("[yellow]No sections found.[/yellow]")
        raise typer.Exit(1)

    table = Table("File", "Line", "Level", "Heading", "Chars", "Images", "Diagrams")
    for sec in sections:
        table.add_row(
            sec.source_file,
            str(sec.line_start),
            f"H{sec.heading_level}",
            sec.heading[:50],
            str(len(sec.content)),
            str(len(sec.images)),
            str(len(sec.diagrams)),
        )
    console.print(table)
    console.print(f"\nTotal: {len(sections)} sections")


@app.command(name="config")
def config_show() -> None:
    """Display current configuration."""
    s = config.settings
    lines = [
        f"  SRC_DIR           = {config.SRC_DIR}",
        f"  OUT_DIR           = {config.OUT_DIR}",
        f"  Anthropic model   = {s.anthropic_model}",
        f"  API key set       = {'Yes' if s.anthropic_api_key else 'No'}",
        f"  Cards / section   = {s.cards_per_section}",
        f"  Deck name         = {s.deck_name}",
        f"  Mermaid binary    = {s.mermaid_bin}",
        f"  PlantUML render   = {s.plantuml_rendering}",
    ]
    console.print("[bold]Configuration[/bold]")
    for line in lines:
        console.print(line)


if __name__ == "__main__":
    app()
