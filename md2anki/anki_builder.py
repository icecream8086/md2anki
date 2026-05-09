"""Build an Anki deck package (``.apkg``) from generated cards."""

from __future__ import annotations

from pathlib import Path

import genanki

from . import config
from .models import Card, Deck

# ── Global CSS variables (shared by all models) ──────────────────────────
GLOBAL_CSS = """
:root {
  --bg: #121212;
  --text: #E0E0E0;
  --text-dim: #999999;
  --text-bright: #FFFFFF;
  --color-neutral: #2D7DD2;
  --color-alert: #D62839;
  --color-success: #2A9D8F;
  --color-emphasis: #F77F00;
  --color-muted-1: #8D9B9A;
  --color-muted-2: #B8A9C9;
  --color-muted-3: #D4A5A5;
  --color-muted-4: #B5C4A1;
  --spacing: 1.5rem;
  --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, 'Inter', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
  font-size: 16px;
  line-height: 1.8;
  padding: var(--spacing);
  min-height: 100%;
}
img { max-width: 100%; display: block; margin: 1em auto; border-radius: 8px; }
code {
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 0.85em;
  background: rgba(255,255,255,0.06);
  padding: 2px 8px;
  border-radius: 6px;
}
hr { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 1.2em 0; }

/* ── fadeIn – one-shot only, no infinite animation ── */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.card {
  animation: fadeIn 0.3s ease-out;
}
"""

# ══════════════════════════════════════════════════════════════════════════
#  1. WORD MODEL — letter-splitting with JS auto-reveal
# ══════════════════════════════════════════════════════════════════════════

WORD_CSS = GLOBAL_CSS + """
.word-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.4em;
  margin: 2em 0;
  min-height: 3em;
}
.letter-group {
  display: inline-block;
  font-size: 2.4em;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-bright);
  background: rgba(255,255,255,0.04);
  padding: 0.1em 0.3em;
  border-radius: var(--radius);
  animation: fadeIn 0.25s ease-out;
}
.letter-group.revealed {
  background: rgba(45,125,210,0.12);
  color: var(--color-neutral);
}
.back-word {
  text-align: center;
}
.back-word .full-word {
  font-size: 2em;
  font-weight: 700;
  color: var(--text-bright);
  margin: 0.5em 0 0.2em;
}
.back-word .phonetic {
  font-size: 1.1em;
  color: var(--text-dim);
  margin-bottom: 0.8em;
}
.back-word .def {
  font-size: 1em;
  color: var(--color-neutral);
  margin: 0.6em 0;
}
.back-word .ex {
  font-size: 0.95em;
  color: var(--color-muted-3);
  font-style: italic;
  margin-top: 0.4em;
}
"""

WORD_FRONT = """\
<div class="word-container" id="letters"></div>
<script>
(function(){
  var word = "{{Front}}".trim();
  if (!word) return;
  var size = word.length <= 6 ? 2 : 3;
  var groups = [];
  for (var i = 0; i < word.length; i += size) {
    groups.push(word.slice(i, i + size));
  }
  var container = document.getElementById('letters');
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
            {"name": "Front"},
            {"name": "word_full"},
            {"name": "word_phonetic"},
            {"name": "word_definition"},
            {"name": "word_example"},
            {"name": "Tags"},
        ],
        templates=[{"name": "Word", "qfmt": WORD_FRONT, "afmt": WORD_BACK}],
        css=WORD_CSS,
    )


# ══════════════════════════════════════════════════════════════════════════
#  2. MATH MODEL — derivation chain, 1 note → 4 cards
# ══════════════════════════════════════════════════════════════════════════

MATH_CSS = GLOBAL_CSS + """
.math-title {
  font-size: 1.1em;
  color: var(--text-dim);
  margin-bottom: 0.3em;
  letter-spacing: 0.04em;
}
.math-step {
  font-size: 1.6em;
  font-weight: 500;
  color: var(--text-bright);
  margin: 1em 0;
  padding: 1em;
  background: rgba(45,125,210,0.06);
  border-left: 4px solid var(--color-neutral);
  border-radius: 0 var(--radius) var(--radius) 0;
  line-height: 1.7;
}
.math-arrow {
  text-align: center;
  font-size: 1.4em;
  color: var(--color-success);
  margin: 0.5em 0;
}
.math-next-label {
  font-size: 0.8em;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 0.5em;
}
"""

MATH_FRONT = """\
<div class="math-title">{{Title}}</div>
<div class="math-step">{{current}}</div>
"""

MATH_BACK = """\
<div class="math-title">{{Title}}</div>
<div class="math-step">{{current}}</div>
<div class="math-arrow">↓</div>
<div class="math-step">{{next}}</div>
<div class="tags">{{Tags}}</div>
"""


def _math_model() -> genanki.Model:
    """4 card templates linking Step1→Step2 … Step4→Step5."""
    templates = []
    for i in range(1, 5):
        cur = f"Step{i}"
        nxt = f"Step{i+1}"
        templates.append({
            "name": f"Step {i}→{i+1}",
            "qfmt": MATH_FRONT.replace("{{current}}", "{{" + cur + "}}"),
            "afmt": MATH_BACK.replace("{{current}}", "{{" + cur + "}}")
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

CONCEPT_CSS = GLOBAL_CSS + """
.concept-front {
  font-size: 2em;
  font-weight: 700;
  color: var(--text-bright);
  text-align: center;
  margin: 1.5em 0;
}
.concept-section {
  margin: 1em 0;
  padding: 0.8em 1em;
  border-radius: var(--radius);
  line-height: 1.7;
}
.concept-section .label {
  font-size: 0.75em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 0.3em;
}
.concept-section .content { font-size: 1em; }
.sec-def    { background: rgba(141,155,154,0.10); }
.sec-def .label    { color: var(--color-muted-1); }
.sec-analogy      { background: rgba(184,169,201,0.10); }
.sec-analogy .label { color: var(--color-muted-2); }
.sec-example      { background: rgba(212,165,165,0.10); }
.sec-example .label { color: var(--color-muted-3); }
.sec-notes        { background: rgba(181,196,161,0.10); }
.sec-notes .label   { color: var(--color-muted-4); }
"""

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
#  Helpers
# ══════════════════════════════════════════════════════════════════════════

def _populate_note(card: Card, model: genanki.Model) -> genanki.Note:
    """Turn a Card into a genanki Note using the right model."""
    if card.type == "word":
        fields = [
            card.front,
            card.word_full or card.front,
            card.word_phonetic,
            card.word_definition,
            card.word_example,
            " ".join(card.tags),
        ]
    elif card.type == "math":
        steps = card.steps[:5]
        while len(steps) < 5:
            steps.append("")
        fields = [card.front, *steps, " ".join(card.tags)]
    else:  # concept
        fields = [
            card.front,
            card.definition or card.back,
            card.analogy,
            card.example,
            card.notes,
            " ".join(card.tags),
        ]

    return genanki.Note(
        model=model,
        fields=fields,
        tags=card.tags,
        guid=genanki.guid_for(card.front + card.back + card.type),
    )


def build_package(deck: Deck) -> Path:
    """Build an ``.apkg`` file and warn if media >100 MB."""
    models = {
        "word": _word_model(),
        "math": _math_model(),
        "concept": _concept_model(),
    }
    anki_deck = genanki.Deck(
        deck_id=hash(deck.name) % (2**31),
        name=deck.name,
    )

    for card in deck.cards:
        ctype = card.type if card.type in models else "concept"
        note = _populate_note(card, models[ctype])
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
