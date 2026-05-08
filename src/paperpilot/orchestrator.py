"""Workflow orchestration using LangGraph.

Defines the state machine that coordinates Parser, Analyst, Compare,
and Search agents. Each workflow is a LangGraph graph that passes
a shared state through a sequence of agent nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperpilot.tools.figure_tools import (
    figures_to_markdown,
    generate_figure_prefix,
    organize_figures,
)
from paperpilot.tools.pdf_tools import (
    PaperMetadata,
    extract_figures,
    extract_metadata,
    extract_references,
    extract_text,
)
from paperpilot.tools.template_tools import render_note, save_note


# ---------------------------------------------------------------------------
# Shared state that flows through the workflow
# ---------------------------------------------------------------------------
@dataclass
class PaperState:
    """State object shared across all agents in a workflow."""

    # Input
    pdf_path: Path = field(default_factory=Path)
    language: str = "zh"

    # Parser Agent output
    metadata: PaperMetadata = field(default_factory=PaperMetadata)
    full_text: str = ""
    figure_paths: list[Path] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    # Analyst Agent output
    summary: str = ""
    abstract_zh: str = ""
    framework: str = ""
    research_question: str = ""
    methods: str = ""
    parameters: dict[str, str] = field(default_factory=dict)
    results: str = ""
    innovations: str = ""
    limitations: str = ""
    key_references: list[str] = field(default_factory=list)

    # Output
    note_path: Path = field(default_factory=Path)


# ---------------------------------------------------------------------------
# Read workflow: PDF -> Parse -> Analyze -> Generate Note
# ---------------------------------------------------------------------------
def run_read_workflow(
    pdf_path: Path,
    output_dir: Path,
    template_name: str = "paper_note.md.j2",
    language: str = "zh",
    extract_figures: bool = True,
) -> dict[str, Any]:
    """Run the full single-paper analysis workflow.

    Flow: PDF -> Parser Agent -> Analyst Agent -> Render Note

    Returns a dict with 'note_path' and 'figures' keys.
    """
    state = PaperState(pdf_path=pdf_path, language=language)

    # Step 1: Parser Agent — extract structured data from PDF
    state = _run_parser(state, extract_figs=extract_figures, output_dir=output_dir)

    # Step 2: Analyst Agent — analyze content with LLM
    state = _run_analyst(state)

    # Step 3: Render note from template
    note_path = _render_and_save(state, output_dir, template_name)
    state.note_path = note_path

    # Step 4: Auto-index into vector store for RAG search
    _index_paper(state)

    return {
        "note_path": str(note_path),
        "figures": [str(p) for p in state.figure_paths],
    }


def run_compare_workflow(
    pdf_paths: list[Path],
    output_path: Path,
    language: str = "zh",
) -> dict[str, Any]:
    """Run the multi-paper comparison workflow.

    Flow:
    1. Parse + analyze each PDF individually (reuses read pipeline)
    2. Send all analyses to Compare Agent for side-by-side comparison
    3. Render comparison table using comparison.md.j2 template

    Args:
        pdf_paths: List of PDF files to compare (2+).
        output_path: Where to save the comparison markdown.
        language: Output language ("zh" or "en").

    Returns:
        Dict with 'output_path' key.
    """
    from rich.console import Console

    console = Console()

    # Step 1: Parse and analyze each paper
    states: list[PaperState] = []
    for i, pdf_path in enumerate(pdf_paths, 1):
        console.print(f"\n[cyan]Paper {i}/{len(pdf_paths)}:[/cyan] {pdf_path.name}")
        state = PaperState(pdf_path=pdf_path, language=language)
        state = _run_parser(state, extract_figs=False, output_dir=output_path.parent)
        state = _run_analyst(state)
        states.append(state)

    # Step 2: Compare Agent
    console.print(f"\n[cyan]Comparing {len(states)} papers...[/cyan]")
    try:
        from paperpilot.agents.compare import compare_papers

        comparison = compare_papers(states, language=language)
    except RuntimeError as e:
        console.print(f"[yellow]LLM unavailable: {e}[/yellow]")
        console.print("[yellow]Generating comparison with metadata only.[/yellow]")
        from paperpilot.agents.compare import compare_papers_fallback

        comparison = compare_papers_fallback(states)
    except Exception as e:
        console.print(f"[red]Comparison failed: {e}[/red]")
        from paperpilot.agents.compare import compare_papers_fallback

        comparison = compare_papers_fallback(states)

    # Step 3: Render comparison
    content = render_note("comparison.md.j2", comparison)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    console.print(f"\n[green]Comparison saved to: {output_path}[/green]")
    return {"output_path": str(output_path)}


def run_search_workflow(
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Run the paper search workflow.

    Combines two sources:
    1. Semantic Scholar API — external search across 200M+ papers
    2. Local vector store (ChromaDB) — semantic search in already-read papers

    Results are merged and deduplicated by DOI.

    Args:
        query: Search keywords.
        limit: Max results from external source.

    Returns:
        List of dicts with keys: title, authors, year, doi, source.
        Each dict also has 'origin' = "semantic_scholar" or "local_library".
    """
    from rich.console import Console

    console = Console()
    results: list[dict[str, Any]] = []

    # Source 1: Semantic Scholar (external)
    try:
        from paperpilot.sources.semantic_scholar import SemanticScholarSource

        console.print("  [dim]Searching Semantic Scholar...[/dim]")
        with SemanticScholarSource() as s2:
            papers = s2.search(query=query, limit=limit)
        for p in papers:
            results.append({
                "title": p.title,
                "authors": ", ".join(p.authors[:3]) + (" et al." if len(p.authors) > 3 else ""),
                "year": p.year,
                "doi": p.doi,
                "source": "semantic_scholar",
                "origin": "semantic_scholar",
            })
        console.print(f"  [dim]Found {len(papers)} external results[/dim]")
    except Exception as e:
        console.print(f"  [yellow]Semantic Scholar search failed: {e}[/yellow]")

    # Source 2: Local vector store (RAG)
    try:
        from paperpilot.store.vector_store import PaperVectorStore

        store = PaperVectorStore()
        if store.count() > 0:
            console.print("  [dim]Searching local library...[/dim]")
            local_results = store.search(query=query, n_results=5)
            # Deduplicate by DOI
            existing_dois = {r["doi"] for r in results if r.get("doi")}
            for paper in local_results:
                if paper.get("doi") and paper["doi"] in existing_dois:
                    continue
                paper["origin"] = "local_library"
                paper["source"] = "local_library"
                results.append(paper)
            console.print(f"  [dim]Found {len(local_results)} local matches[/dim]")
    except Exception:
        pass  # Local store not available — that's fine

    return results


# ---------------------------------------------------------------------------
# Internal workflow steps
# ---------------------------------------------------------------------------
def _run_parser(
    state: PaperState,
    extract_figs: bool,
    output_dir: Path,
) -> PaperState:
    """Parser Agent: extract text, metadata, figures, and references from PDF.

    This step is deterministic (no LLM needed) — pure PDF processing.
    """
    from rich.console import Console
    from rich.progress import Progress

    console = Console()

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Parsing PDF...", total=4)

        # 1. Metadata
        state.metadata = extract_metadata(state.pdf_path)
        progress.update(task, advance=1, description="[cyan]Extracted metadata")

        # 2. Full text
        state.full_text = extract_text(state.pdf_path)
        progress.update(task, advance=1, description="[cyan]Extracted text")

        # 3. Figures
        if extract_figs:
            prefix = generate_figure_prefix(state.metadata.title)
            figures_dir = output_dir / "figures" / prefix
            raw_figures = extract_figures(
                state.pdf_path, figures_dir, prefix=f"{prefix}_"
            )
            state.figure_paths = organize_figures(raw_figures, figures_dir, prefix)
            progress.update(
                task, advance=1, description=f"[cyan]Extracted {len(state.figure_paths)} figures"
            )
        else:
            progress.update(task, advance=1, description="[cyan]Skipped figures")

        # 4. References
        state.references = extract_references(state.pdf_path)
        progress.update(
            task, advance=1, description=f"[cyan]Found {len(state.references)} references"
        )

    console.print(f"[bold]{state.metadata.title}[/bold]")
    console.print(f"Authors: {', '.join(state.metadata.authors)}")
    console.print(f"Pages: {state.metadata.pages}")

    return state


def _run_analyst(state: PaperState) -> PaperState:
    """Analyst Agent: use LLM to analyze paper content.

    Sends the extracted text to Claude/GPT and gets back structured analysis.
    Three possible outcomes:
    1. Success: LLM returns full analysis → all fields populated
    2. No API key: graceful fallback → metadata-only note
    3. API error: partial fallback → whatever we got + error message
    """
    from rich.console import Console

    console = Console()
    console.print("\n[cyan]Analyzing with LLM...[/cyan]")

    try:
        from paperpilot.agents.analyst import analyze_paper

        state = analyze_paper(state)
    except RuntimeError as e:
        # RuntimeError = no API key configured
        console.print(f"[yellow]LLM unavailable: {e}[/yellow]")
        console.print("[yellow]Generating note with metadata only.[/yellow]")
        state = _fill_placeholder(state)
    except Exception as e:
        # Network errors, API errors, parsing failures, etc.
        console.print(f"[red]LLM analysis failed: {e}[/red]")
        console.print("[yellow]Falling back to metadata-only note.[/yellow]")
        state = _fill_placeholder(state)

    return state


def _fill_placeholder(state: PaperState) -> PaperState:
    """Fill analysis fields with placeholder text when LLM is unavailable."""
    state.summary = (
        f"（LLM 分析未执行）论文共 {state.metadata.pages} 页，"
        f"提取到 {len(state.references)} 条参考文献。"
    )
    state.abstract_zh = state.metadata.abstract or "（未提取到摘要）"
    state.framework = "（需要配置 API Key 后重新分析）"
    state.research_question = "（需要配置 API Key 后重新分析）"
    state.methods = "（需要配置 API Key 后重新分析）"
    state.results = "（需要配置 API Key 后重新分析）"
    state.innovations = "（需要配置 API Key 后重新分析）"
    state.limitations = "（需要配置 API Key 后重新分析）"
    return state


def _render_and_save(
    state: PaperState,
    output_dir: Path,
    template_name: str,
) -> Path:
    """Render the analysis into a markdown note and save it."""
    # Build template data
    figures_md = ""
    if state.figure_paths:
        note_dir = output_dir
        figures_md = figures_to_markdown(state.figure_paths, relative_to=note_dir)

    data = {
        "title": state.metadata.title,
        "authors": state.metadata.authors,
        "journal": state.metadata.journal,
        "year": state.metadata.year,
        "doi": state.metadata.doi,
        "summary": state.summary,
        "abstract_zh": state.abstract_zh,
        "framework": state.framework,
        "research_question": state.research_question,
        "methods": state.methods,
        "parameters": state.parameters,
        "results": state.results,
        "innovations": state.innovations,
        "limitations": state.limitations,
        "figures_markdown": figures_md,
        "references": state.key_references or state.references[:10],
    }

    content = render_note(template_name, data)

    # Generate filename from title
    prefix = generate_figure_prefix(state.metadata.title)
    note_path = output_dir / f"{prefix}.md"

    return save_note(content, note_path)


def _index_paper(state: PaperState) -> None:
    """Auto-index an analyzed paper into the vector store for RAG search.

    Called at the end of run_read_workflow(). Failure here is non-fatal —
    the note has already been saved, so we just log and move on.
    """
    try:
        from paperpilot.store.vector_store import PaperVectorStore

        store = PaperVectorStore()
        store.add_paper(state)
    except Exception:
        # Vector store indexing is optional — don't break the main workflow
        pass
