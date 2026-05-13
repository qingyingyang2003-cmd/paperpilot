"""Workflow orchestration using LangGraph StateGraph.

Defines graph-based workflows that coordinate Parser, Analyst, Compare,
and Search agents. Each workflow is a compiled LangGraph graph that passes
a shared state through a sequence of nodes with conditional routing.

Workflows:
- read_graph: PDF → Parse → (Analyze | Skip) → Render → Index
- compare: Parse+Analyze each paper → Compare Agent → Render table
- search: Semantic Scholar + local ChromaDB → deduplicated results
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from paperpilot.config import config
from paperpilot.tools.figure_tools import (
    figures_to_markdown,
    generate_figure_prefix,
    organize_figures,
)
from paperpilot.tools.pdf_tools import (
    extract_figures,
    extract_metadata,
    extract_references,
    extract_text,
)
from paperpilot.tools.template_tools import render_note, save_note

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State definitions
# ---------------------------------------------------------------------------
class PaperState(TypedDict, total=False):
    """State object shared across all nodes in the read workflow.

    Uses TypedDict (LangGraph standard). Nodes receive the full state
    and return a partial dict with only the keys they modify.
    """

    # Input (set before graph invocation)
    pdf_path: str
    language: str
    output_dir: str
    template_name: str
    extract_figs: bool

    # Parser node output
    metadata: dict[str, Any]
    full_text: str
    figure_paths: list[str]
    references: list[str]

    # Analyst node output
    summary: str
    abstract_zh: str
    framework: str
    research_question: str
    methods: str
    parameters: dict[str, str]
    results: str
    innovations: str
    limitations: str
    key_references: list[str]

    # Output
    note_path: str
    llm_available: bool


# ---------------------------------------------------------------------------
# Node functions — each receives full state, returns partial update
# ---------------------------------------------------------------------------
def parse_node(state: PaperState) -> dict[str, Any]:
    """Parser node: extract text, metadata, figures, and references from PDF.

    Deterministic — no LLM needed. Pure PDF processing via PyMuPDF.
    """
    from rich.console import Console
    from rich.progress import Progress

    console = Console()
    pdf_path = Path(state["pdf_path"])
    output_dir = Path(state.get("output_dir", "./notes"))
    do_extract_figs = state.get("extract_figs", True)

    updates: dict[str, Any] = {}

    with Progress(console=console) as progress:
        task = progress.add_task("[cyan]Parsing PDF...", total=4)

        # 1. Metadata
        meta = extract_metadata(pdf_path)
        updates["metadata"] = {
            "title": meta.title,
            "authors": meta.authors,
            "abstract": meta.abstract,
            "doi": meta.doi,
            "journal": meta.journal,
            "year": meta.year,
            "pages": meta.pages,
        }
        progress.update(task, advance=1, description="[cyan]Extracted metadata")

        # 2. Full text
        updates["full_text"] = extract_text(pdf_path)
        progress.update(task, advance=1, description="[cyan]Extracted text")

        # 3. Figures
        if do_extract_figs:
            prefix = generate_figure_prefix(meta.title)
            figures_dir = output_dir / "figures" / prefix
            raw_figures = extract_figures(pdf_path, figures_dir, prefix=f"{prefix}_")
            organized = organize_figures(raw_figures, figures_dir, prefix)
            updates["figure_paths"] = [str(p) for p in organized]
            progress.update(
                task,
                advance=1,
                description=f"[cyan]Extracted {len(organized)} figures",
            )
        else:
            updates["figure_paths"] = []
            progress.update(task, advance=1, description="[cyan]Skipped figures")

        # 4. References
        refs = extract_references(pdf_path)
        updates["references"] = refs
        progress.update(
            task,
            advance=1,
            description=f"[cyan]Found {len(refs)} references",
        )

    # Check if LLM is available (for conditional routing)
    updates["llm_available"] = config.llm.api_key is not None

    console.print(f"[bold]{meta.title}[/bold]")
    console.print(f"Authors: {', '.join(meta.authors)}")
    console.print(f"Pages: {meta.pages}")

    return updates


def analyze_node(state: PaperState) -> dict[str, Any]:
    """Analyst node: use LLM to analyze paper content.

    Sends extracted text to Claude/GPT and gets back structured analysis.
    """
    from rich.console import Console

    from paperpilot.agents.analyst import analyze_paper_from_state

    console = Console()
    console.print("\n[cyan]Analyzing with LLM...[/cyan]")

    try:
        return analyze_paper_from_state(state)
    except Exception as e:
        console.print(f"[red]LLM analysis failed: {e}[/red]")
        console.print("[yellow]Falling back to metadata-only note.[/yellow]")
        return _placeholder_analysis(state)


def skip_analyze_node(state: PaperState) -> dict[str, Any]:
    """Fallback node: fill placeholder text when LLM is unavailable."""
    from rich.console import Console

    console = Console()
    console.print("\n[yellow]No API key configured — skipping LLM analysis.[/yellow]")
    return _placeholder_analysis(state)


def render_node(state: PaperState) -> dict[str, Any]:
    """Render node: generate markdown note from template + analysis data."""
    output_dir = Path(state.get("output_dir", "./notes"))
    template_name = state.get("template_name", "paper_note.md.j2")
    metadata = state.get("metadata", {})
    figure_paths = [Path(p) for p in state.get("figure_paths", [])]

    # Build figures markdown
    figures_md = ""
    if figure_paths:
        figures_md = figures_to_markdown(figure_paths, relative_to=output_dir)

    # Build template data
    data = {
        "title": metadata.get("title", ""),
        "authors": metadata.get("authors", []),
        "journal": metadata.get("journal", ""),
        "year": metadata.get("year", ""),
        "doi": metadata.get("doi", ""),
        "summary": state.get("summary", ""),
        "abstract_zh": state.get("abstract_zh", ""),
        "framework": state.get("framework", ""),
        "research_question": state.get("research_question", ""),
        "methods": state.get("methods", ""),
        "parameters": state.get("parameters", {}),
        "results": state.get("results", ""),
        "innovations": state.get("innovations", ""),
        "limitations": state.get("limitations", ""),
        "figures_markdown": figures_md,
        "references": state.get("key_references") or state.get("references", [])[:10],
    }

    content = render_note(template_name, data)

    # Generate filename and save
    prefix = generate_figure_prefix(metadata.get("title", "paper"))
    note_path = output_dir / f"{prefix}.md"
    saved_path = save_note(content, note_path)

    return {"note_path": str(saved_path)}


def index_node(state: PaperState) -> dict[str, Any]:
    """Index node: auto-index paper into ChromaDB for RAG search.

    Non-fatal — if indexing fails, the note has already been saved.
    """
    try:
        from paperpilot.store.vector_store import PaperVectorStore

        store = PaperVectorStore()
        metadata = state.get("metadata", {})

        # Build a PaperMetadata-like object for the store
        _IndexablePaper = type(
            "_IndexablePaper",
            (),
            {
                "metadata": type(
                    "_Meta",
                    (),
                    {
                        "title": metadata.get("title", ""),
                        "authors": metadata.get("authors", []),
                        "abstract": metadata.get("abstract", ""),
                        "doi": metadata.get("doi", ""),
                        "journal": metadata.get("journal", ""),
                        "year": metadata.get("year", ""),
                    },
                )(),
                "summary": state.get("summary", ""),
                "research_question": state.get("research_question", ""),
                "methods": state.get("methods", ""),
                "note_path": Path(state.get("note_path", "")),
            },
        )

        store.add_paper(_IndexablePaper)
    except Exception as e:
        logger.debug(f"Vector store indexing skipped: {e}")

    return {}


# ---------------------------------------------------------------------------
# Routing function for conditional edges
# ---------------------------------------------------------------------------
def route_after_parse(state: PaperState) -> Literal["analyze", "skip_analyze"]:
    """Route to LLM analysis or placeholder based on API key availability."""
    if state.get("llm_available", False):
        return "analyze"
    return "skip_analyze"


# ---------------------------------------------------------------------------
# Graph construction — the read workflow
# ---------------------------------------------------------------------------
def _build_read_graph() -> StateGraph:
    """Build the LangGraph StateGraph for single-paper analysis.

    Graph structure:
        START → parse → [analyze | skip_analyze] → render → index → END

    The conditional edge after 'parse' checks whether an LLM API key
    is configured. If yes, route to full analysis. If no, route to
    placeholder generation (graceful degradation).
    """
    graph = StateGraph(PaperState)

    # Add nodes
    graph.add_node("parse", parse_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("skip_analyze", skip_analyze_node)
    graph.add_node("render", render_node)
    graph.add_node("index", index_node)

    # Add edges
    graph.add_edge(START, "parse")
    graph.add_conditional_edges(
        "parse",
        route_after_parse,
        {"analyze": "analyze", "skip_analyze": "skip_analyze"},
    )
    graph.add_edge("analyze", "render")
    graph.add_edge("skip_analyze", "render")
    graph.add_edge("render", "index")
    graph.add_edge("index", END)

    return graph


# Compile once at module level for reuse
read_graph = _build_read_graph().compile()


# ---------------------------------------------------------------------------
# Public API — called by CLI
# ---------------------------------------------------------------------------
def run_read_workflow(
    pdf_path: Path,
    output_dir: Path,
    template_name: str = "paper_note.md.j2",
    language: str = "zh",
    extract_figures: bool = True,
) -> dict[str, Any]:
    """Run the full single-paper analysis workflow.

    Invokes the compiled LangGraph read_graph with initial state.

    Returns a dict with 'note_path' and 'figures' keys.
    """
    initial_state: PaperState = {
        "pdf_path": str(pdf_path),
        "language": language,
        "output_dir": str(output_dir),
        "template_name": template_name,
        "extract_figs": extract_figures,
    }

    result = read_graph.invoke(initial_state)

    return {
        "note_path": result.get("note_path", ""),
        "figures": result.get("figure_paths", []),
    }


def run_compare_workflow(
    pdf_paths: list[Path],
    output_path: Path,
    language: str = "zh",
) -> dict[str, Any]:
    """Run the multi-paper comparison workflow.

    Flow:
    1. Invoke read_graph for each PDF (parse + analyze)
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

    # Step 1: Run read graph for each paper (without rendering/indexing)
    states: list[dict[str, Any]] = []
    for i, pdf_path in enumerate(pdf_paths, 1):
        console.print(f"\n[cyan]Paper {i}/{len(pdf_paths)}:[/cyan] {pdf_path.name}")
        initial: PaperState = {
            "pdf_path": str(pdf_path),
            "language": language,
            "output_dir": str(output_path.parent),
            "template_name": "paper_note.md.j2",
            "extract_figs": False,
        }
        result = read_graph.invoke(initial)
        states.append(result)

    # Step 2: Compare Agent
    console.print(f"\n[cyan]Comparing {len(states)} papers...[/cyan]")
    try:
        from paperpilot.agents.compare import compare_papers

        comparison = compare_papers(states, language=language)
    except RuntimeError as e:
        console.print(f"[yellow]LLM unavailable: {e}[/yellow]")
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
            results.append(
                {
                    "title": p.title,
                    "authors": ", ".join(p.authors[:3]) + (" et al." if len(p.authors) > 3 else ""),
                    "year": p.year,
                    "doi": p.doi,
                    "source": "semantic_scholar",
                    "origin": "semantic_scholar",
                }
            )
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
            existing_dois = {r["doi"] for r in results if r.get("doi")}
            for paper in local_results:
                if paper.get("doi") and paper["doi"] in existing_dois:
                    continue
                paper["origin"] = "local_library"
                paper["source"] = "local_library"
                results.append(paper)
            console.print(f"  [dim]Found {len(local_results)} local matches[/dim]")
    except Exception as e:
        logger.debug(f"Local store search skipped: {e}")

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _placeholder_analysis(state: PaperState) -> dict[str, Any]:
    """Generate placeholder analysis when LLM is unavailable."""
    metadata = state.get("metadata", {})
    refs = state.get("references", [])
    return {
        "summary": (
            f"（LLM 分析未执行）论文共 {metadata.get('pages', '?')} 页，"
            f"提取到 {len(refs)} 条参考文献。"
        ),
        "abstract_zh": metadata.get("abstract") or "（未提取到摘要）",
        "framework": "（需要配置 API Key 后重新分析）",
        "research_question": "（需要配置 API Key 后重新分析）",
        "methods": "（需要配置 API Key 后重新分析）",
        "results": "（需要配置 API Key 后重新分析）",
        "innovations": "（需要配置 API Key 后重新分析）",
        "limitations": "（需要配置 API Key 后重新分析）",
    }
