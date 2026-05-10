"""Use Anthropic API to generate flashcards from note sections."""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from . import config
from .models import Card, Section

_PROMPT = """You are a flashcard creator. Given a section of study notes, create \
{cards_per_section} concise flashcards that capture the key concepts.

Classify each card's **type** as one of:
- "word"    — vocabulary, terminology, definition
- "math"    — formula, equation, derivation, theorem
- "concept" — idea, process, explanation, principle
- "cloze"   — fill-in-the-blank (use {{c1::answer}} in `front` for the gap)
- "code"    — code snippet → expected output / explanation
- "diagram" — Venn diagram, SVG animation, flowchart (provide `svg_content`)

### Per-type field rules:
- **concept**: `front` = concept name, `back` = short answer, plus separate `definition`, `analogy`, `example`, `notes`.
- **word**: `front` = word/phrase, plus `word_full`, `word_phonetic`, `word_definition`, `word_example`.  If possible, also return `morphemes` = array of prefix/root/suffix chunks (e.g. ["un", "believe", "able"]).  When the word has no clear morphemes, omit `morphemes` (fallback = letter groups).
- **math**: `front` = short title, plus `steps` array (3-5 ordered derivation steps).
- **cloze**: `front` = sentence with {{c1::gap}}, `back` = full answer, `extra` = grammar note.
- **code**: `front` = question / prompt, `title` = topic, `code` = the snippet, `output` = expected output, `explanation` = brief analysis, `back` = combined (output + explanation).
- **diagram**: `front` = title, `svg_content` = raw SVG markup, `explanation` = what the diagram shows, `back` = explanation.

General rules:
- front should be a short prompt (question / term / incomplete sentence).
- back / answers under 3 sentences.
- Include 1-3 relevant tags (lowercase, hyphens).
- If the note is too short, return at least 1 card.

Return ONLY valid JSON, no other text:
{{"cards": [
  {{"type": "concept", "front": "...", "definition": "...", "analogy": "...", "example": "...", "notes": "...", "tags": ["tag1"]}},
  {{"type": "math", "front": "...", "steps": ["s1", "s2", "s3"], "tags": ["tag1"]}},
  {{"type": "word", "front": "...", "word_full": "...", "word_phonetic": "...", "word_definition": "...", "word_example": "...", "tags": ["tag1"]}},
  {{"type": "cloze", "front": "The {{c1::answer}} is ...", "back": "The answer is correct", "extra": "grammar note", "tags": ["tag1"]}},
  {{"type": "code", "front": "What does this output?", "title": "map example", "code": "[1,2,3].map(x=>x*2)", "output": "[2,4,6]", "explanation": "map doubles each element", "back": "...", "tags": ["js"]}},
  {{"type": "diagram", "front": "Venn: A∩B", "svg_content": "<svg>...</svg>", "explanation": "Intersection of sets A and B", "back": "...", "tags": ["logic"]}}
]}}

Note section: "{heading}"
{content}"""


def generate_cards(sections: list[Section]) -> list[Card]:
    """Call the Anthropic API to produce flashcards for each section."""
    api_key = config.settings.anthropic_api_key
    if not api_key:
        print("  [warn] ANTHROPIC_API_KEY not set – using placeholder cards")
        return _placeholder_cards(sections)

    client = Anthropic(api_key=api_key)
    model = config.settings.anthropic_model
    cards_per_section = config.settings.cards_per_section
    max_chars = config.settings.max_section_chars

    all_cards: list[Card] = []

    for sec in sections:
        content = sec.content[:max_chars] if len(sec.content) > max_chars else sec.content
        if not content.strip():
            continue

        prompt = _PROMPT.format(
            cards_per_section=cards_per_section,
            heading=sec.heading,
            content=content,
        )

        try:
            resp = client.messages.create(
                model=model,
                max_tokens=3000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = _extract_json(resp.content[0].text)
            data: dict[str, Any] = json.loads(raw)
        except Exception as exc:
            print(f"  [warn] AI generation failed for '{sec.heading}': {exc}")
            continue

        for c in data.get("cards", []):
            card_type = c.get("type", "concept")
            card = Card(
                type=card_type,
                front=c.get("front", c.get("question", "")),
                back=c.get("back", c.get("answer", "")),
                tags=c.get("tags", []),
                source_section=sec.heading,
                source_file=sec.source_file,
                media_files=[d.output_svg for d in sec.diagrams if d.output_svg],
            )
            if card_type == "concept":
                card.definition = c.get("definition", "")
                card.analogy = c.get("analogy", "")
                card.example = c.get("example", "")
                card.notes = c.get("notes", "")
            elif card_type == "word":
                card.word_full = c.get("word_full", c.get("front", ""))
                card.word_phonetic = c.get("word_phonetic", "")
                card.word_definition = c.get("word_definition", "")
                card.word_example = c.get("word_example", "")
                card.morphemes = c.get("morphemes", [])
            elif card_type == "math":
                card.steps = c.get("steps", [])
                if not card.steps and card.back:
                    card.steps = [card.front, card.back]
            elif card_type == "cloze":
                card.extra = c.get("extra", "")
            elif card_type == "code":
                card.title = c.get("title", "")
                card.code = c.get("code", "")
                card.output = c.get("output", "")
                card.explanation = c.get("explanation", "")
            elif card_type == "diagram":
                card.title = c.get("title", c.get("front", ""))
                card.svg_content = c.get("svg_content", "")
                card.explanation = c.get("explanation", "")

            all_cards.append(card)

    if not all_cards:
        print("  [warn] No cards generated – using placeholders")
        return _placeholder_cards(sections)

    return all_cards


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    if "{" in text:
        text = text[text.index("{"):]
    if text.rfind("}") != -1:
        text = text[: text.rfind("}") + 1]
    return text.strip()


def _placeholder_cards(sections: list[Section]) -> list[Card]:
    """Fallback: create one simple card per section."""
    cards: list[Card] = []
    for sec in sections:
        if sec.content.strip():
            cards.append(
                Card(
                    front=f"Summarize: {sec.heading}",
                    back=sec.content[:300],
                    tags=["placeholder"],
                    source_section=sec.heading,
                    source_file=sec.source_file,
                )
            )
    return cards
