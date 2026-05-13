"""Tests for the PaperVectorStore (ChromaDB wrapper).

Tests use a temporary directory for ChromaDB persistence,
so no real data is affected and cleanup is automatic.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from paperpilot.store.vector_store import PaperVectorStore, _title_to_id
from paperpilot.tools.pdf_tools import PaperMetadata


# ---------------------------------------------------------------------------
# Test helper — lightweight paper object for vector store tests
# ---------------------------------------------------------------------------
@dataclass
class _TestPaperState:
    """Minimal paper state for testing the vector store."""

    metadata: PaperMetadata = field(default_factory=PaperMetadata)
    summary: str = ""
    research_question: str = ""
    methods: str = ""
    note_path: Path = field(default_factory=Path)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_store(tmp_path: Path) -> PaperVectorStore:
    """A PaperVectorStore backed by a temporary directory."""
    return PaperVectorStore(persist_dir=str(tmp_path / "chroma"))


@pytest.fixture
def sample_state() -> _TestPaperState:
    """A paper state with realistic data for indexing."""
    state = _TestPaperState()
    state.metadata = PaperMetadata(
        title="Nanoscale Surface Charge Visualization of Human Hair",
        authors=["Faduma M. Maddar", "David Perry"],
        journal="Analytical Chemistry",
        year="2019",
        doi="10.1021/acs.analchem.8b05977",
        pages=8,
        abstract="We present a method for nanoscale surface charge mapping of hair.",
    )
    state.summary = "首次用 SICM 实现头发表面电荷纳米级定量可视化"
    state.research_question = "如何在液相环境中对头发表面电荷进行纳米级定量成像？"
    state.methods = "SICM hopping mode + potential-pulse chronoamperometry"
    state.note_path = Path("notes/hair-charge.md")
    return state


@pytest.fixture
def second_state() -> _TestPaperState:
    """A second paper state for multi-paper tests."""
    state = _TestPaperState()
    state.metadata = PaperMetadata(
        title="Surface Charge Visualization at Viable Living Cells",
        authors=["David Perry", "Ashley Page"],
        journal="JACS",
        year="2016",
        doi="10.1021/jacs.6b04065",
        pages=6,
        abstract="We demonstrate surface charge mapping of living cells using SICM.",
    )
    state.summary = "首次在活细胞上实现 SICM 电荷成像"
    state.research_question = "如何对活细胞表面电荷进行纳米级成像？"
    state.methods = "SICM hopping mode with bias modulation"
    state.note_path = Path("notes/cell-charge.md")
    return state


# ---------------------------------------------------------------------------
# Basic operations
# ---------------------------------------------------------------------------
class TestAddAndCount:
    def test_empty_store(self, tmp_store: PaperVectorStore) -> None:
        assert tmp_store.count() == 0

    def test_add_paper(self, tmp_store: PaperVectorStore, sample_state: _TestPaperState) -> None:
        tmp_store.add_paper(sample_state)
        assert tmp_store.count() == 1

    def test_add_multiple(
        self,
        tmp_store: PaperVectorStore,
        sample_state: _TestPaperState,
        second_state: _TestPaperState,
    ) -> None:
        tmp_store.add_paper(sample_state)
        tmp_store.add_paper(second_state)
        assert tmp_store.count() == 2

    def test_upsert_same_doi(
        self, tmp_store: PaperVectorStore, sample_state: _TestPaperState
    ) -> None:
        """Adding the same paper twice (same DOI) should not duplicate."""
        tmp_store.add_paper(sample_state)
        tmp_store.add_paper(sample_state)
        assert tmp_store.count() == 1


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
class TestSearch:
    def test_search_empty_store(self, tmp_store: PaperVectorStore) -> None:
        results = tmp_store.search("SICM")
        assert results == []

    def test_search_finds_relevant(
        self,
        tmp_store: PaperVectorStore,
        sample_state: _TestPaperState,
        second_state: _TestPaperState,
    ) -> None:
        tmp_store.add_paper(sample_state)
        tmp_store.add_paper(second_state)
        results = tmp_store.search("hair surface charge")
        assert len(results) > 0
        # The hair paper should be more relevant
        assert results[0]["title"] == "Nanoscale Surface Charge Visualization of Human Hair"

    def test_search_returns_metadata(
        self, tmp_store: PaperVectorStore, sample_state: _TestPaperState
    ) -> None:
        tmp_store.add_paper(sample_state)
        results = tmp_store.search("SICM")
        assert len(results) == 1
        result = results[0]
        assert result["title"] == "Nanoscale Surface Charge Visualization of Human Hair"
        assert result["year"] == "2019"
        assert result["doi"] == "10.1021/acs.analchem.8b05977"
        assert "distance" in result

    def test_search_respects_n_results(
        self,
        tmp_store: PaperVectorStore,
        sample_state: _TestPaperState,
        second_state: _TestPaperState,
    ) -> None:
        tmp_store.add_paper(sample_state)
        tmp_store.add_paper(second_state)
        results = tmp_store.search("SICM", n_results=1)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# List and remove
# ---------------------------------------------------------------------------
class TestListAndRemove:
    def test_list_empty(self, tmp_store: PaperVectorStore) -> None:
        assert tmp_store.list_papers() == []

    def test_list_papers(
        self,
        tmp_store: PaperVectorStore,
        sample_state: _TestPaperState,
        second_state: _TestPaperState,
    ) -> None:
        tmp_store.add_paper(sample_state)
        tmp_store.add_paper(second_state)
        papers = tmp_store.list_papers()
        assert len(papers) == 2
        titles = {p["title"] for p in papers}
        assert "Nanoscale Surface Charge Visualization of Human Hair" in titles

    def test_remove_paper(self, tmp_store: PaperVectorStore, sample_state: _TestPaperState) -> None:
        tmp_store.add_paper(sample_state)
        assert tmp_store.count() == 1
        tmp_store.remove_paper(sample_state.metadata.doi)
        assert tmp_store.count() == 0

    def test_remove_nonexistent(self, tmp_store: PaperVectorStore) -> None:
        # Should not raise
        tmp_store.remove_paper("nonexistent-doi")
        # ChromaDB may or may not return False for nonexistent IDs
        # The important thing is it doesn't crash


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
class TestTitleToId:
    def test_deterministic(self) -> None:
        id1 = _title_to_id("Test Paper Title")
        id2 = _title_to_id("Test Paper Title")
        assert id1 == id2

    def test_different_titles_different_ids(self) -> None:
        id1 = _title_to_id("Paper A")
        id2 = _title_to_id("Paper B")
        assert id1 != id2

    def test_length(self) -> None:
        result = _title_to_id("Any Title")
        assert len(result) == 16


class TestPaperWithoutDoi:
    def test_add_paper_without_doi(self, tmp_store: PaperVectorStore) -> None:
        """Papers without DOI should use title hash as ID."""
        state = _TestPaperState()
        state.metadata = PaperMetadata(
            title="A Paper Without DOI",
            authors=["Author"],
        )
        state.summary = "Some summary"
        tmp_store.add_paper(state)
        assert tmp_store.count() == 1
