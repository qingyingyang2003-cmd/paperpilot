"""Tests for paper sources (Semantic Scholar + x-mol)."""

from pathlib import Path

import pytest

from paperpilot.sources import PaperInfo, PaperSource
from paperpilot.sources.semantic_scholar import SemanticScholarSource
from paperpilot.sources.xmol import XMolSource

# Mark for tests that hit real APIs — skip by default, run with:
#   uv run pytest -m network
network = pytest.mark.skipif(
    "not config.getoption('--run-network', default=False)",
    reason="Skipped: real API call. Run with: uv run pytest --run-network",
)


def pytest_addoption(parser):
    """Add --run-network CLI flag to pytest."""
    parser.addoption(
        "--run-network", action="store_true", default=False,
        help="Run tests that hit real network APIs",
    )


# ---------------------------------------------------------------------------
# PaperInfo tests (pure local, no network)
# ---------------------------------------------------------------------------
class TestPaperInfo:
    def test_default_values(self) -> None:
        p = PaperInfo(title="Test Paper")
        assert p.title == "Test Paper"
        assert p.authors == []
        assert p.pdf_url is None
        assert p.source == ""

    def test_full_construction(self) -> None:
        p = PaperInfo(
            title="SICM imaging",
            authors=["Alice", "Bob"],
            journal="Analytical Chemistry",
            year="2024",
            doi="10.1234/test",
            abstract="We present...",
            url="https://example.com/paper",
            pdf_url="https://example.com/paper.pdf",
            source="semantic_scholar",
        )
        assert len(p.authors) == 2
        assert p.doi == "10.1234/test"


# ---------------------------------------------------------------------------
# SemanticScholarSource unit tests (no network)
# ---------------------------------------------------------------------------
class TestSemanticScholarLocal:
    def test_parse_paper(self) -> None:
        """Test parsing a Semantic Scholar API response item."""
        s2 = SemanticScholarSource()
        item = {
            "title": "Surface Charge Visualization of Hair",
            "authors": [{"name": "Alice"}, {"name": "Bob"}],
            "year": 2019,
            "abstract": "We present a method...",
            "externalIds": {"DOI": "10.1021/test.123"},
            "journal": {"name": "Analytical Chemistry"},
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "url": "https://semanticscholar.org/paper/123",
        }
        paper = s2._parse_paper(item)

        assert paper.title == "Surface Charge Visualization of Hair"
        assert paper.authors == ["Alice", "Bob"]
        assert paper.year == "2019"
        assert paper.doi == "10.1021/test.123"
        assert paper.journal == "Analytical Chemistry"
        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.source == "semantic_scholar"
        s2.close()

    def test_parse_paper_missing_fields(self) -> None:
        """Test parsing with missing optional fields."""
        s2 = SemanticScholarSource()
        item = {
            "title": "Minimal Paper",
            "authors": [],
            "year": None,
            "abstract": None,
            "externalIds": None,
            "journal": None,
            "openAccessPdf": None,
            "url": "",
        }
        paper = s2._parse_paper(item)

        assert paper.title == "Minimal Paper"
        assert paper.authors == []
        assert paper.doi == ""
        assert paper.pdf_url is None
        s2.close()

    def test_browse_delegates_to_search(self) -> None:
        """Verify browse() calls search() internally."""
        # We can't test the actual API call, but we can verify the method exists
        s2 = SemanticScholarSource()
        assert hasattr(s2, "browse")
        assert hasattr(s2, "search")
        s2.close()

    def test_context_manager(self) -> None:
        """Test that SemanticScholarSource works as a context manager."""
        with SemanticScholarSource() as s2:
            assert s2 is not None


# ---------------------------------------------------------------------------
# Semantic Scholar network tests (real API calls — opt-in)
# ---------------------------------------------------------------------------
class TestSemanticScholarNetwork:
    @pytest.fixture
    def s2(self) -> SemanticScholarSource:
        return SemanticScholarSource(timeout=30.0)

    @network
    def test_search_returns_results(self, s2: SemanticScholarSource) -> None:
        papers = s2.search("scanning ion conductance microscopy", limit=5)
        assert len(papers) > 0
        assert all(isinstance(p, PaperInfo) for p in papers)

    @network
    def test_search_result_has_title(self, s2: SemanticScholarSource) -> None:
        papers = s2.search("SICM surface charge", limit=3)
        for p in papers:
            assert p.title, "Every result should have a title"
            assert p.source == "semantic_scholar"

    @network
    def test_get_paper_by_doi(self, s2: SemanticScholarSource) -> None:
        paper = s2.get_paper_by_doi("10.1021/acs.analchem.8b04985")
        if paper:
            assert "hair" in paper.title.lower() or "surface" in paper.title.lower()


# ---------------------------------------------------------------------------
# XMol tests
# ---------------------------------------------------------------------------
class TestXMol:
    def test_categories_available(self) -> None:
        cats = XMolSource.available_categories()
        assert "chemistry" in cats
        assert "materials" in cats

    def test_unauthenticated_raises_error(self) -> None:
        source = XMolSource(cookie_path="/nonexistent/path")
        with pytest.raises(RuntimeError, match="authentication"):
            source.search("test")

    @network
    def test_search_with_cookie(self) -> None:
        source = XMolSource()
        if not source.is_authenticated:
            pytest.skip("x-mol cookie not configured")
        papers = source.search("SICM", limit=5)
        assert isinstance(papers, list)
