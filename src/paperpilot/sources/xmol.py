"""X-MOL paper source.

Scrapes x-mol.com for paper search and category browsing.
Requires user-provided cookies for authentication (x-mol has login walls
and captcha protection).

Cookie setup:
1. Log in to x-mol.com in your browser
2. Open DevTools (F12) -> Network tab -> copy Cookie header value
3. Save to ~/.paperpilot/xmol_cookie.txt
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from paperpilot.sources import PaperInfo, PaperSource

# Known x-mol category URL slugs
XMOL_CATEGORIES = {
    "chemistry": "chemistry",
    "materials": "materials",
    "physics": "physics",
    "biology": "biology",
    "medicine": "medicine",
    "cs": "cs",
    "engineering": "engineering",
    "math": "math",
    "environment": "environment",
    "energy": "energy",
}

XMOL_BASE = "https://www.x-mol.com"


class XMolSource(PaperSource):
    """Paper source backed by x-mol.com web scraping.

    Requires a valid cookie file for authentication.
    """

    def __init__(
        self,
        cookie_path: str | Path = "~/.paperpilot/xmol_cookie.txt",
        timeout: float = 30.0,
    ) -> None:
        self._cookie_path = Path(cookie_path).expanduser()
        self._timeout = timeout
        self._cookies = self._load_cookies()

    def _load_cookies(self) -> dict[str, str]:
        """Load cookies from the cookie file.

        The file should contain the raw Cookie header value, e.g.:
        SESSION_ID=abc123; user_token=xyz789; ...
        """
        if not self._cookie_path.exists():
            return {}

        raw = self._cookie_path.read_text(encoding="utf-8").strip()
        cookies: dict[str, str] = {}
        for pair in raw.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, _, value = pair.partition("=")
                cookies[key.strip()] = value.strip()
        return cookies

    def _get_client(self) -> httpx.Client:
        """Create an HTTP client with x-mol cookies and headers."""
        return httpx.Client(
            timeout=self._timeout,
            cookies=self._cookies,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://www.x-mol.com/",
            },
            follow_redirects=True,
        )

    @property
    def is_authenticated(self) -> bool:
        """Check if cookies are loaded."""
        return len(self._cookies) > 0

    def search(self, query: str, limit: int = 10) -> list[PaperInfo]:
        """Search papers on x-mol by keyword.

        Sends a request to x-mol's search endpoint and parses the HTML response.
        """
        if not self.is_authenticated:
            raise RuntimeError(
                "x-mol requires authentication. "
                f"Please save your cookie to: {self._cookie_path}\n"
                "Steps: Login x-mol in browser -> F12 -> Network -> "
                "copy Cookie header -> paste into the file"
            )

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "beautifulsoup4 is required for x-mol. "
                "Install it with: uv add beautifulsoup4"
            )

        with self._get_client() as client:
            response = client.get(
                f"{XMOL_BASE}/paper/search",
                params={"q": query, "page": 1},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_paper_list(soup, limit=limit)

    def browse(self, category: str, page: int = 1) -> list[PaperInfo]:
        """Browse latest papers in a category on x-mol.

        Args:
            category: Category name (e.g., "chemistry", "materials").
                      See XMOL_CATEGORIES for available options.
            page: Page number.
        """
        if not self.is_authenticated:
            raise RuntimeError(
                "x-mol requires authentication. "
                f"Please save your cookie to: {self._cookie_path}"
            )

        slug = XMOL_CATEGORIES.get(category.lower(), category)

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required for x-mol.")

        with self._get_client() as client:
            response = client.get(
                f"{XMOL_BASE}/paper/{slug}",
                params={"page": page},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            return self._parse_paper_list(soup)

    def _parse_paper_list(
        self,
        soup: "BeautifulSoup",
        limit: int = 20,
    ) -> list[PaperInfo]:
        """Parse a list of papers from x-mol HTML.

        x-mol paper list pages typically have paper cards with:
        - Title (linked to detail page)
        - Authors
        - Journal name and year
        - Abstract snippet
        - DOI link

        The exact HTML structure may change over time. This parser
        tries multiple common selectors for robustness.
        """
        papers: list[PaperInfo] = []

        # Try common selectors for paper cards on x-mol
        # x-mol uses various class names across different page types
        card_selectors = [
            "div.paper-item",
            "div.search-item",
            "div.paper_list_item",
            "div.article-item",
            "li.paper-item",
        ]

        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                break

        # Fallback: look for any div containing paper-like content
        if not cards:
            cards = self._find_paper_cards_heuristic(soup)

        for card in cards[:limit]:
            paper = self._parse_single_card(card)
            if paper and paper.title:
                papers.append(paper)

        return papers

    def _parse_single_card(self, card: "Tag") -> PaperInfo | None:
        """Parse a single paper card element into PaperInfo."""
        try:
            # Title: usually the first <a> with substantial text
            title = ""
            url = ""
            for a_tag in card.find_all("a"):
                text = a_tag.get_text(strip=True)
                if len(text) > 20:  # Paper titles are usually long
                    title = text
                    href = a_tag.get("href", "")
                    url = href if href.startswith("http") else f"{XMOL_BASE}{href}"
                    break

            if not title:
                return None

            # Authors: look for author-related elements
            authors: list[str] = []
            for selector in [".author", ".authors", "[class*=author]"]:
                author_el = card.select_one(selector)
                if author_el:
                    raw = author_el.get_text(strip=True)
                    authors = [a.strip() for a in re.split(r"[,;，；]", raw) if a.strip()]
                    break

            # Journal and year
            journal = ""
            year = ""
            for selector in [".journal", ".source", "[class*=journal]", ".pub-info"]:
                journal_el = card.select_one(selector)
                if journal_el:
                    journal = journal_el.get_text(strip=True)
                    # Try to extract year from journal text
                    year_match = re.search(r"20\d{2}", journal)
                    if year_match:
                        year = year_match.group(0)
                    break

            # DOI
            doi = ""
            for a_tag in card.find_all("a", href=True):
                href = a_tag["href"]
                doi_match = re.search(r"10\.\d{4,}/[^\s\"']+", href)
                if doi_match:
                    doi = doi_match.group(0)
                    break

            # Abstract
            abstract = ""
            for selector in [".abstract", ".summary", "[class*=abstract]", "p"]:
                abs_el = card.select_one(selector)
                if abs_el:
                    text = abs_el.get_text(strip=True)
                    if len(text) > 50:  # Abstracts are usually long
                        abstract = text
                        break

            return PaperInfo(
                title=title,
                authors=authors,
                journal=journal,
                year=year,
                doi=doi,
                abstract=abstract,
                url=url,
                pdf_url=None,  # x-mol doesn't directly host PDFs
                source="xmol",
            )
        except Exception:
            return None

    def _find_paper_cards_heuristic(self, soup: "BeautifulSoup") -> list:
        """Fallback: find paper-like content blocks using heuristics.

        Looks for <div> or <li> elements that contain both a link
        with long text (title) and DOI-like patterns.
        """
        candidates = []
        for el in soup.find_all(["div", "li"]):
            text = el.get_text()
            has_long_link = any(
                len(a.get_text(strip=True)) > 20 for a in el.find_all("a")
            )
            has_doi = bool(re.search(r"10\.\d{4,}/", text))
            if has_long_link and (has_doi or len(text) > 200):
                candidates.append(el)
        return candidates

    @staticmethod
    def available_categories() -> dict[str, str]:
        """Return available x-mol category names and their URL slugs."""
        return dict(XMOL_CATEGORIES)
