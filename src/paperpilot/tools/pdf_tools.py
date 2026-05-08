"""PDF parsing tools for extracting text, metadata, figures, and references.

Uses PyMuPDF (fitz) as the PDF backend. These functions are designed to be
called as tools by the Parser Agent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class PaperMetadata:
    """Structured metadata extracted from a PDF."""

    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    doi: str = ""
    journal: str = ""
    year: str = ""
    pages: int = 0


def extract_metadata(pdf_path: str | Path) -> PaperMetadata:
    """Extract metadata (title, authors, abstract, DOI) from a PDF.

    Strategy:
    1. Try PDF built-in metadata first (many publishers embed it).
    2. Fall back to heuristics on the first page text.
    """
    doc = fitz.open(str(pdf_path))
    meta = doc.metadata or {}

    # --- Title ---
    title = meta.get("title", "").strip()
    if not title:
        # Heuristic: largest font text on page 1 is usually the title
        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]
        max_size = 0.0
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if span["size"] > max_size:
                        max_size = span["size"]
                        title = span["text"]

    # --- Authors ---
    raw_author = meta.get("author", "")
    authors = [a.strip() for a in re.split(r"[,;]", raw_author) if a.strip()]

    # --- Abstract ---
    full_first_pages = ""
    for i in range(min(2, len(doc))):
        full_first_pages += doc[i].get_text()
    abstract = _extract_abstract(full_first_pages)

    # --- DOI ---
    doi = ""
    doi_match = re.search(r"10\.\d{4,}/[^\s]+", full_first_pages)
    if doi_match:
        doi = doi_match.group(0).rstrip(".")

    # --- Year ---
    year = meta.get("creationDate", "")[:4] if meta.get("creationDate") else ""

    metadata = PaperMetadata(
        title=title,
        authors=authors,
        abstract=abstract,
        doi=doi,
        journal=meta.get("producer", ""),
        year=year,
        pages=len(doc),
    )
    doc.close()
    return metadata


def extract_text(pdf_path: str | Path) -> str:
    """Extract full text content from all pages of a PDF.

    Returns the concatenated text with page markers.
    """
    doc = fitz.open(str(pdf_path))
    parts: list[str] = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            parts.append(f"--- Page {i + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(parts)


def extract_figures(
    pdf_path: str | Path,
    output_dir: str | Path,
    dpi: int = 300,
    prefix: str = "",
) -> list[Path]:
    """Extract images/figures from a PDF and save as PNG files.

    Two strategies:
    1. Extract embedded images directly (higher quality).
    2. If no embedded images found, render pages containing figures as PNG.

    Returns a list of saved file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))

    saved: list[Path] = []

    # Strategy 1: extract embedded images
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        images = page.get_images(full=True)
        for img_idx, img_info in enumerate(images):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            if base_image is None:
                continue

            image_bytes = base_image["image"]
            ext = base_image.get("ext", "png")

            # Skip tiny images (logos, icons) — likely not figures
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            if width < 100 or height < 100:
                continue

            filename = f"{prefix}p{page_idx + 1}_img{img_idx + 1}.{ext}"
            filepath = output_dir / filename
            filepath.write_bytes(image_bytes)
            saved.append(filepath)

    # Strategy 2: if no embedded images, render full pages as PNG
    if not saved:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=mat)
            filename = f"{prefix}page_{page_idx + 1}.png"
            filepath = output_dir / filename
            pix.save(str(filepath))
            saved.append(filepath)

    doc.close()
    return saved


def extract_references(pdf_path: str | Path) -> list[str]:
    """Extract reference list from the end of a PDF.

    Heuristic: find the 'References' section and parse numbered entries.
    """
    doc = fitz.open(str(pdf_path))
    full_text = ""
    # References are usually in the last few pages
    start_page = max(0, len(doc) - 5)
    for i in range(start_page, len(doc)):
        full_text += doc[i].get_text()
    doc.close()

    # Find the references section
    ref_match = re.search(
        r"(?:References|REFERENCES|Bibliography|参考文献)\s*\n",
        full_text,
    )
    if not ref_match:
        return []

    ref_text = full_text[ref_match.end() :]

    # Parse numbered references: [1], (1), 1., etc.
    refs = re.split(r"\n\s*[\[\(]?\d+[\]\).]?\s+", ref_text)
    # Clean up
    cleaned = []
    for ref in refs:
        ref = ref.strip().replace("\n", " ")
        ref = re.sub(r"\s+", " ", ref)
        if len(ref) > 20:  # Skip too-short fragments
            cleaned.append(ref)

    return cleaned


def _extract_abstract(text: str) -> str:
    """Extract abstract from paper text using common patterns."""
    patterns = [
        r"(?:Abstract|ABSTRACT)[:\s]*\n?(.*?)(?:\n\s*(?:Keywords|KEYWORDS|Introduction|INTRODUCTION|1[\.\s]))",
        r"(?:Abstract|ABSTRACT)[:\s]*\n?(.*?)(?:\n\n)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            abstract = match.group(1).strip()
            abstract = re.sub(r"\s+", " ", abstract)
            if len(abstract) > 50:
                return abstract
    return ""
