"""Figure management tools for organizing and embedding extracted images.

Works on top of pdf_tools.extract_figures() to provide higher-level
figure management: renaming, markdown embedding, and directory organization.
"""

from __future__ import annotations

import re
from pathlib import Path


def generate_figure_prefix(paper_title: str) -> str:
    """Generate a short, filesystem-safe prefix from a paper title.

    Example: "Nanoscale Surface Charge Visualization of Human Hair"
             -> "nanoscale-surface-charge"
    """
    # Lowercase, keep only alphanumeric and spaces
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", paper_title.lower())
    words = clean.split()[:4]  # First 4 words
    return "-".join(words) if words else "paper"


def figures_to_markdown(
    figure_paths: list[Path],
    relative_to: Path | None = None,
) -> str:
    """Generate markdown image syntax for a list of figure paths.

    Args:
        figure_paths: List of absolute or relative paths to figure images.
        relative_to: If provided, paths are made relative to this directory.
                     Useful for embedding in notes that live in a different folder.

    Returns:
        Markdown string with all figures embedded.
    """
    lines: list[str] = []
    for i, fig_path in enumerate(figure_paths, 1):
        if relative_to:
            display_path = _relative_path(fig_path, relative_to)
        else:
            display_path = str(fig_path)

        # Use filename (without extension) as alt text
        alt_text = fig_path.stem.replace("_", " ").replace("-", " ").title()
        lines.append(f"![{alt_text}]({display_path})")

    return "\n\n".join(lines)


def organize_figures(
    figure_paths: list[Path],
    target_dir: Path,
    prefix: str,
) -> list[Path]:
    """Rename and move figures to a target directory with consistent naming.

    Renames files to: {prefix}_fig{N}.{ext}
    Returns the list of new file paths.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    new_paths: list[Path] = []

    for i, src in enumerate(figure_paths, 1):
        ext = src.suffix
        new_name = f"{prefix}_fig{i}{ext}"
        dst = target_dir / new_name
        # Copy instead of move to avoid breaking other references
        dst.write_bytes(src.read_bytes())
        new_paths.append(dst)

    return new_paths


def _relative_path(target: Path, base: Path) -> str:
    """Compute a relative path from base to target, handling different roots."""
    try:
        return str(target.relative_to(base))
    except ValueError:
        # Different roots — use os.path.relpath logic
        import os

        return os.path.relpath(str(target), str(base))
