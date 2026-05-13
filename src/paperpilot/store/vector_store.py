"""Paper vector store backed by ChromaDB.

Stores paper embeddings locally for semantic search (RAG).
When a user runs `paperpilot read`, the analyzed paper is automatically
indexed here. Later, `paperpilot search` can find relevant papers
from the local library in addition to external sources.

Design decisions:
- ChromaDB runs locally, zero config, data persists to disk
- Uses ChromaDB's default embedding model (all-MiniLM-L6-v2, runs locally)
- Each paper is one document: title + abstract + summary + methods
- Metadata stored alongside for display (title, authors, year, doi, note_path)
- Graceful degradation: if ChromaDB fails, the rest of the app still works
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from paperpilot.orchestrator import PaperState

# Default persist directory (relative to cwd)
DEFAULT_PERSIST_DIR = ".paperpilot/chroma"

# ChromaDB collection name
COLLECTION_NAME = "paperpilot_papers"


class PaperVectorStore:
    """Local vector store for analyzed papers.

    Wraps ChromaDB to provide:
    - add_paper(): index a paper after analysis
    - search(): semantic search across indexed papers
    - list_papers(): show all indexed papers
    - remove_paper(): delete by DOI

    ChromaDB handles embedding (all-MiniLM-L6-v2) and persistence
    automatically — no external API calls needed.
    """

    def __init__(self, persist_dir: str | Path = DEFAULT_PERSIST_DIR) -> None:
        import chromadb

        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "PaperPilot analyzed papers"},
        )

    def add_paper(self, state: PaperState) -> None:
        """Index a paper after analysis.

        Combines key text fields into a single document for embedding.
        Stores metadata for display in search results.

        Args:
            state: PaperState with metadata and analysis fields filled.
        """
        # Build the document text for embedding
        # Combine the most semantically meaningful fields
        parts = [
            f"Title: {state.metadata.title}",
        ]
        if state.metadata.abstract:
            parts.append(f"Abstract: {state.metadata.abstract}")
        if state.summary:
            parts.append(f"Summary: {state.summary}")
        if state.research_question:
            parts.append(f"Research Question: {state.research_question}")
        if state.methods:
            parts.append(f"Methods: {state.methods}")

        document = "\n\n".join(parts)

        # Use DOI as unique ID if available, otherwise use title hash
        doc_id = state.metadata.doi if state.metadata.doi else _title_to_id(state.metadata.title)

        # Metadata for display (ChromaDB metadata values must be str/int/float/bool)
        metadata: dict[str, str | int | float | bool] = {
            "title": state.metadata.title or "",
            "authors": ", ".join(state.metadata.authors) if state.metadata.authors else "",
            "year": state.metadata.year or "",
            "doi": state.metadata.doi or "",
            "journal": state.metadata.journal or "",
            "note_path": str(state.note_path) if state.note_path else "",
        }

        # Upsert: if paper already exists (same DOI), update it
        self._collection.upsert(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata],
        )

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Semantic search across indexed papers.

        Args:
            query: Natural language search query.
            n_results: Maximum number of results.

        Returns:
            List of dicts with keys: title, authors, year, doi,
            journal, note_path, distance (lower = more relevant).
        """
        if self._collection.count() == 0:
            return []

        # Don't request more results than we have documents
        actual_n = min(n_results, self._collection.count())

        results = self._collection.query(
            query_texts=[query],
            n_results=actual_n,
        )

        papers: list[dict[str, Any]] = []
        if results["metadatas"] and results["distances"]:
            for metadata, distance in zip(
                results["metadatas"][0],
                results["distances"][0],
            ):
                paper = dict(metadata)
                paper["distance"] = distance
                papers.append(paper)

        return papers

    def list_papers(self) -> list[dict[str, Any]]:
        """List all indexed papers.

        Returns:
            List of dicts with paper metadata.
        """
        if self._collection.count() == 0:
            return []

        all_data = self._collection.get()
        papers: list[dict[str, Any]] = []
        if all_data["metadatas"]:
            for metadata in all_data["metadatas"]:
                papers.append(dict(metadata))
        return papers

    def remove_paper(self, doi: str) -> bool:
        """Remove a paper by DOI.

        Args:
            doi: The DOI of the paper to remove.

        Returns:
            True if paper was found and removed, False otherwise.
        """
        try:
            self._collection.delete(ids=[doi])
            return True
        except Exception:
            return False

    def count(self) -> int:
        """Return the number of indexed papers."""
        return self._collection.count()


def _title_to_id(title: str) -> str:
    """Generate a stable ID from a paper title.

    Used when DOI is not available. Takes first 8 chars of
    a simple hash to keep IDs short but unique enough.
    """
    import hashlib

    return hashlib.sha256(title.encode()).hexdigest()[:16]
