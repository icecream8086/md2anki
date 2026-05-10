from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel


class CodeBlock(BaseModel):
    language: str = ""
    content: str


class ImageRef(BaseModel):
    alt_text: str = ""
    src: str


class DiagramBlock(BaseModel):
    kind: str  # "mermaid" | "plantuml"
    content: str
    output_svg: str = ""


class Section(BaseModel):
    heading: str = "Untitled"
    heading_level: int = 1
    content: str = ""
    code_blocks: list[CodeBlock] = []
    images: list[ImageRef] = []
    diagrams: list[DiagramBlock] = []
    source_file: str = ""
    line_start: int = 0


class Card(BaseModel):
    """A single flashcard with type-specific fields."""
    type: str = "concept"  # "word" | "math" | "concept" | "cloze" | "code" | "diagram"
    front: str = ""
    back: str = ""
    tags: list[str] = []
    source_section: str = ""
    source_file: str = ""
    media_files: list[str] = []

    # Concept
    definition: str = ""
    analogy: str = ""
    example: str = ""
    notes: str = ""

    # Math derivation
    steps: list[str] = []

    # Word
    word_full: str = ""
    word_phonetic: str = ""
    word_definition: str = ""
    word_example: str = ""
    morphemes: list[str] = []  # prefix/root/suffix chunks for display

    # Cloze / Grammar
    extra: str = ""

    # Code / Pseudocode
    title: str = ""
    code: str = ""
    output: str = ""
    explanation: str = ""

    # Diagram / SVG
    svg_content: str = ""


class Deck(BaseModel):
    name: str = "Markdown Notes"
    cards: list[Card] = []
    media_paths: list[Path] = []
