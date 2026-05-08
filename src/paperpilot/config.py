"""PaperPilot configuration management.

Loads settings from environment variables or a .env file.
Users set their API keys via:
    export ANTHROPIC_API_KEY=sk-xxx
    export OPENAI_API_KEY=sk-xxx
Or by creating a .env file in the project root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Default directories
DEFAULT_OUTPUT_DIR = Path("./notes")
DEFAULT_FIGURES_DIR = Path("./figures")
DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class LLMConfig:
    """LLM provider configuration.

    All fields can be overridden via environment variables:
        PAPERPILOT_PROVIDER=deepseek
        PAPERPILOT_MODEL=deepseek-chat
    """

    provider: str = "anthropic"  # "anthropic", "openai", or "deepseek"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    max_tokens: int = 8192

    def __post_init__(self) -> None:
        """Allow env vars to override defaults at runtime."""
        self.provider = os.getenv("PAPERPILOT_PROVIDER", self.provider)
        self.model = os.getenv("PAPERPILOT_MODEL", self.model)

    @property
    def api_key(self) -> str | None:
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif self.provider == "deepseek":
            return os.getenv("DEEPSEEK_API_KEY")
        return os.getenv("OPENAI_API_KEY")


@dataclass
class SourceConfig:
    """Paper source configuration."""

    default_source: str = "semantic_scholar"  # "semantic_scholar" or "xmol"
    xmol_cookie_path: Path = Path("~/.paperpilot/xmol_cookie.txt")
    download_dir: Path = Path("./papers")
    auto_analyze: bool = False  # Auto-run 'read' after downloading PDF


@dataclass
class Config:
    """Global PaperPilot configuration."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    source: SourceConfig = field(default_factory=SourceConfig)
    output_dir: Path = DEFAULT_OUTPUT_DIR
    figures_dir: Path = DEFAULT_FIGURES_DIR
    template_dir: Path = DEFAULT_TEMPLATE_DIR
    language: str = "zh"  # "zh" for Chinese, "en" for English
    figure_dpi: int = 300

    def ensure_dirs(self) -> None:
        """Create output directories if they don't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.source.download_dir.mkdir(parents=True, exist_ok=True)


# Singleton config instance — import and use directly
config = Config()
