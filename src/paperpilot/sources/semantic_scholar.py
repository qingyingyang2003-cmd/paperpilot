"""Semantic Scholar paper source.

Uses the free Semantic Scholar Academic Graph API to search papers
and find open-access PDFs. No API key required (rate limit: 100 req/5min).

API docs: https://api.semanticscholar.org/api-docs/graph
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from paperpilot.sources import PaperInfo, PaperSource

# Semantic Scholar API base URL
S2_API = "https://api.semanticscholar.org/graph/v1"

# Fields to request from the API
S2_FIELDS = "title,authors,year,abstract,externalIds,journal,openAccessPdf,url"

# Unpaywall API for finding open-access PDFs
UNPAYWALL_API = "https://api.unpaywall.org/v2"
UNPAYWALL_EMAIL = "paperpilot@example.com"  # Required by Unpaywall TOS

# Retry settings for rate limiting (HTTP 429)
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry


class SemanticScholarSource(PaperSource):
    """Paper source backed by the Semantic Scholar API.

    Features:
    - Free, no API key needed
    - Covers 200M+ papers across all fields
    - Returns open-access PDF links when available
    - Falls back to Unpaywall for additional open-access coverage
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.Client(
            base_url=S2_API,
            timeout=timeout,
            headers={"User-Agent": "PaperPilot/0.1.0"},
        )

    def search(self, query: str, limit: int = 10) -> list[PaperInfo]:
        """Search papers by keyword using Semantic Scholar API.

        Args:
            query: Search keywords (e.g., "SICM surface charge").
            limit: Max results (API max is 100).

        Returns:
            List of PaperInfo with metadata and open-access PDF links.
        """
        data = self._request_with_retry(
            "/paper/search",
            params={
                "query": query,
                "limit": min(limit, 100),
                "fields": S2_FIELDS,
            },
        )

        papers: list[PaperInfo] = []
        for item in data.get("data", []):
            paper = self._parse_paper(item)
            papers.append(paper)

        return papers

    def browse(self, category: str, page: int = 1) -> list[PaperInfo]:
        """Browse is not supported by Semantic Scholar API.

        Semantic Scholar doesn't have category browsing like x-mol.
        Use search() with broad keywords instead.
        """
        # Use category as a search query as a reasonable fallback
        return self.search(query=category, limit=20)

    def download_pdf(self, paper: PaperInfo, output_dir: Path) -> Path | None:
        """Download PDF, trying open-access sources.

        Strategy:
        1. Use Semantic Scholar's openAccessPdf link if available
        2. Try Unpaywall API to find an open-access version
        3. Return None if no free PDF found
        """
        # Strategy 1: already have a PDF URL from S2
        if paper.pdf_url:
            result = super().download_pdf(paper, output_dir)
            if result:
                return result

        # Strategy 2: try Unpaywall
        if paper.doi:
            pdf_url = self._find_unpaywall_pdf(paper.doi)
            if pdf_url:
                paper.pdf_url = pdf_url
                return super().download_pdf(paper, output_dir)

        return None

    def get_paper_by_doi(self, doi: str) -> PaperInfo | None:
        """Fetch a single paper by DOI.

        Useful for enriching references extracted from PDFs.
        """
        try:
            data = self._request_with_retry(
                f"/paper/DOI:{doi}",
                params={"fields": S2_FIELDS},
            )
            return self._parse_paper(data)
        except httpx.HTTPError:
            return None

    def _parse_paper(self, item: dict) -> PaperInfo:
        """Convert a Semantic Scholar API response item to PaperInfo."""
        # Extract authors
        authors = [a.get("name", "") for a in item.get("authors", [])]

        # Extract DOI from externalIds
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI", "")

        # Extract journal name
        journal_info = item.get("journal") or {}
        journal = journal_info.get("name", "") if isinstance(journal_info, dict) else ""

        # Extract open-access PDF URL
        oa_pdf = item.get("openAccessPdf") or {}
        pdf_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None

        return PaperInfo(
            title=item.get("title", ""),
            authors=authors,
            journal=journal,
            year=str(item.get("year", "")),
            doi=doi,
            abstract=item.get("abstract", "") or "",
            url=item.get("url", ""),
            pdf_url=pdf_url,
            source="semantic_scholar",
        )

    def _request_with_retry(self, path: str, params: dict) -> dict:
        """Send a GET request with automatic retry on rate limiting (429).

        Semantic Scholar allows 100 requests per 5 minutes. When exceeded,
        it returns HTTP 429. This method waits and retries with exponential
        backoff: 2s -> 4s -> 8s.
        """
        for attempt in range(MAX_RETRIES + 1):
            response = self._client.get(path, params=params)
            if response.status_code == 429 and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json()
        # Should not reach here, but satisfy type checker
        response.raise_for_status()
        return response.json()

    def _find_unpaywall_pdf(self, doi: str) -> str | None:
        """Query Unpaywall API for an open-access PDF link.

        Unpaywall is a legal service that finds free versions of papers
        (author self-archives, preprints, green/gold open access).
        """
        try:
            response = httpx.get(
                f"{UNPAYWALL_API}/{doi}",
                params={"email": UNPAYWALL_EMAIL},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()

            # best_oa_location has the most accessible version
            best = data.get("best_oa_location") or {}
            pdf_url = best.get("url_for_pdf")
            if pdf_url:
                return pdf_url

            # Try other OA locations
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    return loc["url_for_pdf"]

        except httpx.HTTPError:
            pass

        return None

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> SemanticScholarSource:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
