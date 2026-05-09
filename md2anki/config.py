from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_prefix="MD2ANKI_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Directories (relative to project root)
    src_dir: str = "src"
    out_dir: str = "out"

    # Card generation
    cards_per_section: int = 3
    max_section_chars: int = 4000

    # Anki
    deck_name: str = "Markdown Notes"
    anki_model_name: str = "md2anki Model"

    # Diagram rendering
    mermaid_bin: str = "mmdc"
    plantuml_jar: str = ""
    plantuml_rendering: str = "python"  # "python" | "jar"

    # Media
    media_dir_name: str = "media"


settings = Settings()

# --- Derive absolute paths from project root ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / settings.src_dir
OUT_DIR = PROJECT_ROOT / settings.out_dir
MEDIA_DIR = OUT_DIR / settings.media_dir_name
