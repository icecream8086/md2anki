"""Build an Anki deck package (``.apkg``) from generated cards.

CSS styles are loaded from separate files in ``templates/`` so they can be
tweaked without touching Python code.
"""

from __future__ import annotations

import json
from pathlib import Path

import genanki

from . import config
from .models import Card, Deck

_HERE = Path(__file__).resolve().parent


def _load_css(name: str) -> str:
    """Load a CSS template file, falling back to empty string."""
    path = _HERE / "templates" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# Loaded once at module init
GLOBAL_CSS = _load_css("global.css")
WORD_CSS = GLOBAL_CSS + _load_css("word.css")
MATH_CSS = GLOBAL_CSS + _load_css("math.css")
CONCEPT_CSS = GLOBAL_CSS + _load_css("concept.css")
CLOZE_CSS = GLOBAL_CSS + _load_css("cloze.css")
CODE_CSS = GLOBAL_CSS + _load_css("code.css")
DIAGRAM_CSS = GLOBAL_CSS + _load_css("diagram.css")


# ══════════════════════════════════════════════════════════════════════════
#  1. WORD MODEL — letter-splitting with JS auto-reveal
# ══════════════════════════════════════════════════════════════════════════

WORD_FRONT = """\
<div class="word-container" id="letters"></div>
<script>
(function(){
  var word = "{{Front}}".trim();
  if (!word) return;
  var container = document.getElementById('letters');

  // Try morpheme display first
  var raw = "{{Morphemes}}".trim();
  if (raw && raw !== "[]") {
    try {
      var parts = JSON.parse(raw);
      if (Array.isArray(parts) && parts.length > 0) {
        var labels = ['prefix', 'root', 'suffix', 'unk'];
        parts.forEach(function(p, i) {
          var cls = 'morpheme-' + (labels[i] || 'unk');
          var span = document.createElement('span');
          span.className = 'letter-group ' + cls;
          span.textContent = p;
          container.appendChild(span);
          if (i < parts.length - 1) {
            var dot = document.createElement('span');
            dot.className = 'morpheme-sep';
            dot.textContent = '-';
            container.appendChild(dot);
          }
        });
        return;
      }
    } catch(e) {}
  }

  // Fallback: letter groups
  var size = word.length <= 6 ? 2 : 3;
  var groups = [];
  for (var i = 0; i < word.length; i += size) {
    groups.push(word.slice(i, i + size));
  }
  var idx = 0;
  function showNext() {
    if (idx >= groups.length) return;
    var span = document.createElement('span');
    span.className = 'letter-group';
    span.textContent = groups[idx];
    container.appendChild(span);
    idx++;
    setTimeout(showNext, 400);
  }
  showNext();
  container.addEventListener('click', function(){
    while (container.firstChild) container.removeChild(container.firstChild);
    for (var j = 0; j < groups.length; j++) {
      var s = document.createElement('span');
      s.className = 'letter-group revealed';
      s.textContent = groups[j];
      container.appendChild(s);
    }
  });
})();
</script>
"""

WORD_BACK = """\
{{#Front}}
<div class="back-word">
  <div class="full-word">{{word_full}}</div>
  <div class="phonetic">{{word_phonetic}}</div>
  <hr>
  <div class="def">{{word_definition}}</div>
  <div class="ex">{{word_example}}</div>
</div>
{{/Front}}
<div class="tags">{{Tags}}</div>
"""


def _word_model() -> genanki.Model:
    return genanki.Model(
        model_id=hash("md2anki_word") % (2**31),
        name="md2anki_word",
        fields=[
            {"name": "Front"}, {"name": "word_full"}, {"name": "word_phonetic"},
            {"name": "word_definition"}, {"name": "word_example"},
            {"name": "Morphemes"}, {"name": "Tags"},
        ],
        templates=[{"name": "Word", "qfmt": WORD_FRONT, "afmt": WORD_BACK}],
        css=WORD_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  2. MATH MODEL — derivation chain, 1 note → 4 cards
# ══════════════════════════════════════════════════════════════════════════

MATH_FRONT_TPL = """\
<div class="math-title">{{Title}}</div>
<div class="math-step">{{current}}</div>
"""
MATH_BACK_TPL = """\
<div class="math-title">{{Title}}</div>
<div class="math-step">{{current}}</div>
<div class="math-arrow">↓</div>
<div class="math-step">{{next}}</div>
<div class="tags">{{Tags}}</div>
"""


def _math_model() -> genanki.Model:
    templates = []
    for i in range(1, 5):
        cur, nxt = f"Step{i}", f"Step{i+1}"
        templates.append({
            "name": f"Step {i}→{i+1}",
            "qfmt": MATH_FRONT_TPL.replace("{{current}}", "{{" + cur + "}}"),
            "afmt": MATH_BACK_TPL.replace("{{current}}", "{{" + cur + "}}")
                                 .replace("{{next}}", "{{" + nxt + "}}"),
        })
    return genanki.Model(
        model_id=hash("md2anki_math") % (2**31),
        name="md2anki_math",
        fields=[{"name": "Title"}, {"name": "Step1"}, {"name": "Step2"},
                {"name": "Step3"}, {"name": "Step4"}, {"name": "Step5"},
                {"name": "Tags"}],
        templates=templates,
        css=MATH_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  3. CONCEPT MODEL — definition / analogy / example / notes
# ══════════════════════════════════════════════════════════════════════════

CONCEPT_FRONT = """\
<div class="concept-front">{{Front}}</div>
"""
CONCEPT_BACK = """\
<div class="concept-front">{{Front}}</div>
<hr>
{{#Definition}}
<div class="concept-section sec-def">
  <div class="label">定义</div>
  <div class="content">{{Definition}}</div>
</div>
{{/Definition}}
{{#Analogy}}
<div class="concept-section sec-analogy">
  <div class="label">比喻</div>
  <div class="content">{{Analogy}}</div>
</div>
{{/Analogy}}
{{#Example}}
<div class="concept-section sec-example">
  <div class="label">例子</div>
  <div class="content">{{Example}}</div>
</div>
{{/Example}}
{{#Notes}}
<div class="concept-section sec-notes">
  <div class="label">笔记</div>
  <div class="content">{{Notes}}</div>
</div>
{{/Notes}}
<div class="tags">{{Tags}}</div>
"""


def _concept_model() -> genanki.Model:
    return genanki.Model(
        model_id=hash("md2anki_concept") % (2**31),
        name="md2anki_concept",
        fields=[{"name": "Front"}, {"name": "Definition"}, {"name": "Analogy"},
                {"name": "Example"}, {"name": "Notes"}, {"name": "Tags"}],
        templates=[{"name": "Concept", "qfmt": CONCEPT_FRONT, "afmt": CONCEPT_BACK}],
        css=CONCEPT_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  4. CLOZE MODEL — grammar / sentence fill-in
# ══════════════════════════════════════════════════════════════════════════

CLOZE_QFRONT = """\
<div class="cloze-reveal">{{cloze:Text}}</div>
"""
CLOZE_AFRONT = """\
<div class="cloze-reveal">{{cloze:Text}}</div>
<hr>
{{#Extra}}
<div class="cloze-extra">
  <div class="label">语法笔记</div>
  <div>{{Extra}}</div>
</div>
{{/Extra}}
<div class="tags">{{Tags}}</div>
"""


def _cloze_model() -> genanki.Model:
    return genanki.Model(
        model_id=hash("md2anki_cloze") % (2**31),
        name="md2anki_cloze",
        model_type=genanki.Model.CLOZE,
        fields=[{"name": "Text"}, {"name": "Extra"}, {"name": "Tags"}],
        templates=[{"name": "Cloze", "qfmt": CLOZE_QFRONT, "afmt": CLOZE_AFRONT}],
        css=CLOZE_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  5. CODE MODEL — code output / pseudocode
# ══════════════════════════════════════════════════════════════════════════

CODE_FRONT = """\
{{#Title}}<div class="code-topic">{{Title}}</div>{{/Title}}
<div class="code-block">{{Code}}</div>
"""
CODE_BACK = """\
{{#Title}}<div class="code-topic">{{Title}}</div>{{/Title}}
<div class="code-block">{{Code}}</div>
{{#Output}}
<div class="output-block">{{Output}}</div>
{{/Output}}
{{#Explanation}}
<div class="explanation-block">{{Explanation}}</div>
{{/Explanation}}
<div class="tags">{{Tags}}</div>
"""


def _code_model() -> genanki.Model:
    return genanki.Model(
        model_id=hash("md2anki_code") % (2**31),
        name="md2anki_code",
        fields=[{"name": "Title"}, {"name": "Code"}, {"name": "Output"},
                {"name": "Explanation"}, {"name": "Tags"}],
        templates=[{"name": "Code", "qfmt": CODE_FRONT, "afmt": CODE_BACK}],
        css=CODE_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  6. DIAGRAM MODEL — SVG / Venn / flow / animation
# ══════════════════════════════════════════════════════════════════════════

DIAGRAM_FRONT = """\
{{#Title}}<div class="diagram-title">{{Title}}</div>{{/Title}}
<div class="diagram-svg">{{SvgContent}}</div>
"""
DIAGRAM_BACK = """\
{{#Title}}<div class="diagram-title">{{Title}}</div>{{/Title}}
<div class="diagram-svg">{{SvgContent}}</div>
{{#Explanation}}
<div class="diagram-explanation">{{Explanation}}</div>
{{/Explanation}}
<div class="tags">{{Tags}}</div>
"""


def _diagram_model() -> genanki.Model:
    return genanki.Model(
        model_id=hash("md2anki_diagram") % (2**31),
        name="md2anki_diagram",
        fields=[{"name": "Title"}, {"name": "SvgContent"},
                {"name": "Explanation"}, {"name": "Tags"}],
        templates=[{"name": "Diagram", "qfmt": DIAGRAM_FRONT, "afmt": DIAGRAM_BACK}],
        css=DIAGRAM_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  Note builder & package assembly
# ══════════════════════════════════════════════════════════════════════════

_MODELS = {
    "word": _word_model(),
    "math": _math_model(),
    "concept": _concept_model(),
    "cloze": _cloze_model(),
    "code": _code_model(),
    "diagram": _diagram_model(),
}


def _populate_note(card: Card) -> genanki.Note:
    """Turn a Card into a genanki Note, selecting model by card.type."""
    model = _MODELS.get(card.type, _MODELS["concept"])

    if card.type == "word":
        fields = [card.front, card.word_full or card.front,
                  card.word_phonetic, card.word_definition,
                  card.word_example,
                  json.dumps(card.morphemes, ensure_ascii=False),
                  " ".join(card.tags)]
    elif card.type == "math":
        steps = (card.steps[:5] + [""] * 5)[:5]
        fields = [card.front, *steps, " ".join(card.tags)]
    elif card.type == "cloze":
        fields = [card.front, card.extra or card.back, " ".join(card.tags)]
    elif card.type == "code":
        fields = [card.title, card.code, card.output,
                  card.explanation, " ".join(card.tags)]
    elif card.type == "diagram":
        fields = [card.title or card.front, card.svg_content,
                  card.explanation or card.back, " ".join(card.tags)]
    else:  # concept
        fields = [card.front, card.definition or card.back,
                  card.analogy, card.example, card.notes, " ".join(card.tags)]

    return genanki.Note(
        model=model,
        fields=fields,
        tags=card.tags,
        guid=genanki.guid_for(card.front + card.back + card.type),
    )


def build_package(deck: Deck) -> Path:
    """Build an ``.apkg`` file and warn if media >100 MB."""
    anki_deck = genanki.Deck(
        deck_id=hash(deck.name) % (2**31),
        name=deck.name,
    )

    for card in deck.cards:
        note = _populate_note(card)
        anki_deck.add_note(note)

    media_files = [str(p) for p in deck.media_paths]
    package = genanki.Package(anki_deck)
    package.media_files = media_files

    out_path = config.OUT_DIR / f"{deck.name.replace(' ', '_')}.apkg"
    package.write_to_file(str(out_path))

    _check_media_size(media_files)
    return out_path


def _check_media_size(paths: list[str]) -> None:
    total = sum(Path(p).stat().st_size for p in paths if Path(p).exists())
    if total > 100 * 1024 * 1024:
        mb = total / (1024 * 1024)
        print(f"  [warn] Media exceeds 100 MB ({mb:.1f} MB). Optimise images.")
