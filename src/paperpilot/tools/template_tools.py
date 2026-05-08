"""Template rendering tools for generating markdown notes.

Uses Jinja2 to render structured paper analysis data into markdown files
based on customizable templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from paperpilot.config import config


def get_template_env(template_dir: Path | None = None) -> Environment:
    """Create a Jinja2 environment for loading templates.

    Args:
        template_dir: Directory containing .md.j2 template files.
                      Defaults to the built-in templates directory.
    """
    search_path = str(template_dir or config.template_dir)
    return Environment(
        loader=FileSystemLoader(search_path),
        autoescape=select_autoescape([]),  # No escaping for markdown
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def render_note(
    template_name: str,
    data: dict[str, Any],
    template_dir: Path | None = None,
) -> str:
    """Render a paper note from a template and structured data.

    Args:
        template_name: Template filename (e.g., "paper_note.md.j2").
        data: Dictionary containing the analysis results. Expected keys:
              - title, authors, journal, year, doi
              - summary (one-paragraph summary)
              - abstract_zh (Chinese translation of abstract)
              - framework (logical structure of the paper)
              - research_question
              - methods
              - results
              - innovations
              - limitations
              - figures_markdown (pre-rendered figure embeds)
              - references (list of reference strings)
        template_dir: Optional custom template directory.

    Returns:
        Rendered markdown string.
    """
    env = get_template_env(template_dir)
    template = env.get_template(template_name)
    return template.render(**data)


def save_note(
    content: str,
    output_path: str | Path,
) -> Path:
    """Save rendered markdown content to a file.

    Creates parent directories if needed.
    Returns the absolute path of the saved file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path.resolve()


def list_templates(template_dir: Path | None = None) -> list[str]:
    """List all available template files."""
    search_dir = template_dir or config.template_dir
    return [f.name for f in Path(search_dir).glob("*.md.j2")]
