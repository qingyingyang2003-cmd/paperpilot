"""Paper source abstraction layer.

Defines the common interface (PaperSource ABC) and data model (PaperInfo)
that all paper sources must implement. This enables the Strategy Pattern:
CLI code calls source.search() without knowing whether it's x-mol or
Semantic Scholar underneath.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class PaperInfo:
    """Structured information about a paper from any source."""

    title: str
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    doi: str = ""
    abstract: str = ""
    url: str = ""  # Paper detail page URL
    pdf_url: str | None = None  # Direct PDF link (may be None)
    source: str = ""  # "xmol" / "semantic_scholar"


class PaperSource(ABC):
    """Abstract base class for all paper sources.

    Every source must implement search() and browse().
    download_pdf() has a default implementation that downloads from pdf_url.
    """

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[PaperInfo]:
        """Search papers by keyword query.

        Args:
            query: Search keywords (e.g., "SICM surface charge hair").
            limit: Maximum number of results to return.

        Returns:
            List of PaperInfo objects matching the query.
        """
        ...

    @abstractmethod
    def browse(self, category: str, page: int = 1) -> list[PaperInfo]:
        """Browse papers by category/subject.

        Args:
            category: Subject category (e.g., "chemistry", "materials").
            page: Page number for pagination.

        Returns:
            List of PaperInfo objects in the category.
        """
        ...

    def download_pdf(self, paper: PaperInfo, output_dir: Path) -> Path | None:
        """Download the PDF for a paper.

        Default implementation: download from paper.pdf_url if available.
        Subclasses can override for source-specific download logic.

        Args:
            paper: PaperInfo with pdf_url set.
            output_dir: Directory to save the PDF.

        Returns:
            Path to the downloaded PDF, or None if download failed.
        """
        if not paper.pdf_url:
            return None

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename from DOI or title
        if paper.doi:
            safe_name = paper.doi.replace("/", "_").replace(".", "_")
        else:
            safe_name = "".join(c if c.isalnum() or c == " " else "" for c in paper.title)
            safe_name = "_".join(safe_name.split()[:5])
        filename = f"{safe_name}.pdf"
        filepath = output_dir / filename

        # Download
        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                response = client.get(paper.pdf_url)
                response.raise_for_status()

                # Verify it's actually a PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type and not response.content[:5] == b"%PDF-":
                    return None

                filepath.write_bytes(response.content)
                return filepath
        except (httpx.HTTPError, OSError):
            return None
