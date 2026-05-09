"""Render Mermaid and PlantUML diagrams to SVG."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from . import config
from .models import DiagramBlock


def render_diagrams(diagrams: list[DiagramBlock], out_dir: Path) -> list[DiagramBlock]:
    """Render each unresolved diagram block to SVG in *out_dir*.

    Modifies and returns the same list with ``output_svg`` filled in.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, diag in enumerate(diagrams):
        if diag.output_svg:
            continue  # already rendered

        stem = f"diagram_{i:03d}"
        svg_path = out_dir / f"{stem}.svg"

        if diag.kind == "mermaid":
            _render_mermaid(diag.content, svg_path)
        elif diag.kind == "plantuml":
            _render_plantuml(diag.content, svg_path)

        if svg_path.exists():
            diag.output_svg = svg_path.name

    return diagrams


def _render_mermaid(source: str, out_path: Path) -> None:
    """Render Mermaid definition via the ``mmdc`` CLI."""
    mmdc = config.settings.mermaid_bin
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".mmd", delete=False, encoding="utf-8"
    ) as f:
        f.write(source)
        mmd_path = f.name

    try:
        subprocess.run(
            [mmdc, "-i", mmd_path, "-o", str(out_path), "-q"],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError:
        print(
            f"  [warn] mmdc not found at '{mmdc}' – install mermaid-cli via "
            f"`npm install -g @mermaid-js/mermaid-cli`"
        )
    except subprocess.CalledProcessError as exc:
        print(f"  [warn] Mermaid rendering failed: {exc.stderr.decode().strip()}")
    finally:
        Path(mmd_path).unlink(missing_ok=True)


def _render_plantuml(source: str, out_path: Path) -> None:
    """Render PlantUML definition to SVG.

    Uses the ``plantuml`` Python package by default, or falls back to
    ``java -jar plantuml.jar`` if configured.
    """
    mode = config.settings.plantuml_rendering

    if mode == "python":
        try:
            import plantuml as plantuml_mod  # noqa: N813

            # plantuml Python package expects a full PUML block including @startxyz/@endxyz
            wrapped = source
            if not wrapped.strip().startswith("@start"):
                wrapped = f"@startuml\n{wrapped}\n@enduml"

            proc = subprocess.run(
                ["plantuml", "-tsvg", "-pipe"],
                input=wrapped,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                out_path.write_bytes(proc.stdout.encode("utf-8"))
            else:
                print(f"  [warn] PlantUML pipe rendering failed")
        except ImportError:
            print("  [warn] plantuml Python package not available")
    else:
        jar = config.settings.plantuml_jar
        if not jar:
            print("  [warn] plantuml_jar not configured")
            return
        wrapped = source
        if not wrapped.strip().startswith("@start"):
            wrapped = f"@startuml\n{wrapped}\n@enduml"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".puml", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapped)
            puml_path = f.name
        try:
            subprocess.run(
                ["java", "-jar", jar, "-tsvg", "-o", str(out_path.parent), puml_path],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except subprocess.CalledProcessError as exc:
            print(f"  [warn] PlantUML (jar) failed: {exc.stderr.decode().strip()}")
        finally:
            Path(puml_path).unlink(missing_ok=True)
