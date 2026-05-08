"""Tests for PDF parsing tools."""

from pathlib import Path

import pytest

from paperpilot.tools.pdf_tools import (
    extract_figures,
    extract_metadata,
    extract_references,
    extract_text,
)

# Use a real PDF from the user's research project for integration testing
SAMPLE_PDF = Path("/mnt/d/Research and study assistant/References/nanoscale-surface-charge-visualization-of-human-hair.pdf")


@pytest.fixture
def sample_pdf() -> Path:
    """Provide a sample PDF path, skip if not available."""
    if not SAMPLE_PDF.exists():
        pytest.skip("Sample PDF not found — run tests in the project environment")
    return SAMPLE_PDF


@pytest.fixture
def tmp_figures_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for figure extraction."""
    return tmp_path / "figures"


class TestExtractMetadata:
    def test_returns_paper_metadata(self, sample_pdf: Path) -> None:
        meta = extract_metadata(sample_pdf)
        assert meta.title, "Title should not be empty"
        assert meta.pages > 0, "Should have at least 1 page"

    def test_extracts_abstract(self, sample_pdf: Path) -> None:
        meta = extract_metadata(sample_pdf)
        # Abstract might be empty depending on PDF structure,
        # but the function should not crash
        assert isinstance(meta.abstract, str)

    def test_extracts_doi(self, sample_pdf: Path) -> None:
        meta = extract_metadata(sample_pdf)
        # DOI format: 10.xxxx/xxxxx
        if meta.doi:
            assert meta.doi.startswith("10."), f"Invalid DOI format: {meta.doi}"


class TestExtractText:
    def test_returns_nonempty_text(self, sample_pdf: Path) -> None:
        text = extract_text(sample_pdf)
        assert len(text) > 100, "Should extract substantial text"

    def test_contains_page_markers(self, sample_pdf: Path) -> None:
        text = extract_text(sample_pdf)
        assert "--- Page 1 ---" in text


class TestExtractFigures:
    def test_extracts_images(self, sample_pdf: Path, tmp_figures_dir: Path) -> None:
        figures = extract_figures(sample_pdf, tmp_figures_dir)
        assert len(figures) > 0, "Should extract at least one figure"
        for fig in figures:
            assert fig.exists(), f"Figure file should exist: {fig}"
            assert fig.stat().st_size > 0, f"Figure should not be empty: {fig}"

    def test_skips_tiny_images(self, sample_pdf: Path, tmp_figures_dir: Path) -> None:
        figures = extract_figures(sample_pdf, tmp_figures_dir)
        # All extracted figures should be real figures, not tiny icons
        for fig in figures:
            assert fig.stat().st_size > 1000, f"Figure too small, likely an icon: {fig}"


class TestExtractReferences:
    def test_returns_list(self, sample_pdf: Path) -> None:
        refs = extract_references(sample_pdf)
        assert isinstance(refs, list)

    def test_references_are_strings(self, sample_pdf: Path) -> None:
        refs = extract_references(sample_pdf)
        for ref in refs:
            assert isinstance(ref, str)
            assert len(ref) > 20, f"Reference too short: {ref}"
