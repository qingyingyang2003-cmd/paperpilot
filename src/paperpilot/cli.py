"""PaperPilot CLI — the main entry point for users.

Usage:
    paperpilot read paper.pdf              # Analyze a single paper
    paperpilot read paper.pdf -o notes/    # Specify output directory
    paperpilot compare a.pdf b.pdf c.pdf   # Compare multiple papers
    paperpilot search "SICM surface charge"  # Search related papers
    paperpilot fetch "SICM surface charge"   # Fetch papers from online sources
    paperpilot browse chemistry --source xmol  # Browse by category
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from paperpilot.sources import PaperSource

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="paperpilot",
    help="AI-powered scientific paper analysis agent.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def read(
    pdf_path: Annotated[Path, typer.Argument(help="Path to the PDF file to analyze")],
    output_dir: Annotated[
        Path, typer.Option("-o", "--output", help="Output directory for notes")
    ] = Path("./notes"),
    template: Annotated[
        str | None,
        typer.Option("-t", "--template", help="Custom template file name"),
    ] = None,
    language: Annotated[str, typer.Option("-l", "--lang", help="Output language: zh or en")] = "zh",
    extract_figures: Annotated[
        bool, typer.Option("--figures/--no-figures", help="Extract figures from PDF")
    ] = True,
) -> None:
    """Analyze a single paper and generate structured notes."""
    if not pdf_path.exists():
        console.print(f"[red]Error:[/red] File not found: {pdf_path}")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]Analyzing:[/bold] {pdf_path.name}",
            title="PaperPilot",
            border_style="blue",
        )
    )

    # Import here to avoid slow startup when just showing --help
    from paperpilot.orchestrator import run_read_workflow

    result = run_read_workflow(
        pdf_path=pdf_path,
        output_dir=output_dir,
        template_name=template or "paper_note.md.j2",
        language=language,
        extract_figures=extract_figures,
    )

    console.print(f"\n[green]Done![/green] Note saved to: {result['note_path']}")
    if result.get("figures"):
        console.print(f"[green]Figures:[/green] {len(result['figures'])} images extracted")


@app.command()
def compare(
    pdf_paths: Annotated[list[Path], typer.Argument(help="PDF files to compare (2 or more)")],
    output: Annotated[Path, typer.Option("-o", "--output", help="Output file path")] = Path(
        "./comparison.md"
    ),
    language: Annotated[str, typer.Option("-l", "--lang", help="Output language: zh or en")] = "zh",
) -> None:
    """Compare multiple papers and generate a comparison table."""
    if len(pdf_paths) < 2:
        console.print("[red]Error:[/red] Need at least 2 papers to compare.")
        raise typer.Exit(1)

    for p in pdf_paths:
        if not p.exists():
            console.print(f"[red]Error:[/red] File not found: {p}")
            raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]Comparing {len(pdf_paths)} papers[/bold]",
            title="PaperPilot",
            border_style="blue",
        )
    )

    from paperpilot.orchestrator import run_compare_workflow

    result = run_compare_workflow(
        pdf_paths=pdf_paths,
        output_path=output,
        language=language,
    )

    console.print(f"\n[green]Done![/green] Comparison saved to: {result['output_path']}")


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query for finding papers")],
    limit: Annotated[int, typer.Option("-n", "--limit", help="Max number of results")] = 10,
) -> None:
    """Search for related papers using Semantic Scholar + local library."""
    console.print(
        Panel(
            f'[bold]Searching:[/bold] "{query}"',
            title="PaperPilot",
            border_style="blue",
        )
    )

    from paperpilot.orchestrator import run_search_workflow

    results = run_search_workflow(query=query, limit=limit)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    # Split results by origin
    external = [r for r in results if r.get("origin") != "local_library"]
    local = [r for r in results if r.get("origin") == "local_library"]

    # Display external results
    if external:
        console.print(f"\n[bold cyan]Semantic Scholar ({len(external)} results)[/bold cyan]")
        for i, paper in enumerate(external, 1):
            console.print(f"\n  [bold]{i}.[/bold] {paper['title']}")
            console.print(f"     Authors: {paper.get('authors', 'N/A')}")
            console.print(f"     Year: {paper.get('year', 'N/A')}")
            if paper.get("doi"):
                console.print(f"     DOI: {paper['doi']}")

    # Display local library matches
    if local:
        console.print(f"\n[bold green]Local Library ({len(local)} matches)[/bold green]")
        for i, paper in enumerate(local, 1):
            console.print(f"\n  [bold]{i}.[/bold] {paper.get('title', 'N/A')}")
            console.print(f"     Year: {paper.get('year', 'N/A')}")
            if paper.get("note_path"):
                console.print(f"     Note: {paper['note_path']}")


if __name__ == "__main__":
    app()


# ---------------------------------------------------------------------------
# Helper: create a paper source by name
# ---------------------------------------------------------------------------
def _get_source(name: str) -> PaperSource:
    """Create a PaperSource instance by name."""
    from paperpilot.config import config

    if name == "xmol":
        from paperpilot.sources.xmol import XMolSource

        return XMolSource(cookie_path=config.source.xmol_cookie_path)
    else:
        from paperpilot.sources.semantic_scholar import SemanticScholarSource

        return SemanticScholarSource()


# ---------------------------------------------------------------------------
# fetch command
# ---------------------------------------------------------------------------
@app.command()
def fetch(
    query: Annotated[str, typer.Argument(help="Search keywords for finding papers")],
    source: Annotated[
        str,
        typer.Option("-s", "--source", help="Paper source: semantic_scholar or xmol"),
    ] = "semantic_scholar",
    limit: Annotated[int, typer.Option("-n", "--limit", help="Max number of results")] = 10,
    download: Annotated[
        bool, typer.Option("--download/--no-download", help="Download PDFs")
    ] = False,
    analyze: Annotated[
        bool,
        typer.Option("--analyze/--no-analyze", help="Auto-analyze downloaded PDFs"),
    ] = False,
    output_dir: Annotated[Path, typer.Option("-o", "--output", help="Download directory")] = Path(
        "./papers"
    ),
) -> None:
    """Search and fetch papers from online sources."""
    from rich.table import Table

    console.print(
        Panel(
            f'[bold]Fetching:[/bold] "{query}" from {source}',
            title="PaperPilot",
            border_style="blue",
        )
    )

    src = _get_source(source)
    try:
        papers = src.search(query=query, limit=limit)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not papers:
        console.print("[yellow]No results found.[/yellow]")

    # Display results as a table
    table = Table(title=f"Search Results ({len(papers)} papers)")
    table.add_column("#", style="bold", width=3)
    table.add_column("Title", max_width=60)
    table.add_column("Authors", max_width=30)
    table.add_column("Year", width=6)
    table.add_column("PDF", width=4)

    for i, p in enumerate(papers, 1):
        authors_str = ", ".join(p.authors[:3])
        if len(p.authors) > 3:
            authors_str += " et al."
        pdf_icon = "[green]Y[/green]" if p.pdf_url else "[dim]-[/dim]"
        table.add_row(str(i), p.title, authors_str, p.year, pdf_icon)

    console.print(table)

    # Download PDFs if requested
    if download:
        console.print(f"\n[cyan]Downloading PDFs to {output_dir}...[/cyan]")
        downloaded: list[Path] = []
        for p in papers:
            result = src.download_pdf(p, output_dir)
            if result:
                console.print(f"  [green]OK[/green] {result.name}")
                downloaded.append(result)
            elif p.doi:
                console.print(
                    f"  [yellow]--[/yellow] {p.title[:50]}... (no open-access PDF, DOI: {p.doi})"
                )

        console.print(f"\n[green]Downloaded {len(downloaded)}/{len(papers)} PDFs[/green]")

        # Auto-analyze if requested
        if analyze and downloaded:
            console.print("\n[cyan]Analyzing downloaded papers...[/cyan]")
            from paperpilot.orchestrator import run_read_workflow

            for pdf_path in downloaded:
                try:
                    result = run_read_workflow(
                        pdf_path=pdf_path,
                        output_dir=Path("./notes"),
                        template_name="paper_note.md.j2",
                        language="zh",
                        extract_figures=True,
                    )
                    console.print(f"  [green]OK[/green] {pdf_path.name} -> {result['note_path']}")
                except Exception as e:
                    console.print(f"  [red]Error[/red] {pdf_path.name}: {e}")


# ---------------------------------------------------------------------------
# browse command
# ---------------------------------------------------------------------------
@app.command()
def browse(
    category: Annotated[
        str, typer.Argument(help="Subject category (e.g., chemistry, materials, physics)")
    ],
    source: Annotated[
        str,
        typer.Option("-s", "--source", help="Paper source (xmol recommended)"),
    ] = "xmol",
    page: Annotated[int, typer.Option("-p", "--page", help="Page number")] = 1,
) -> None:
    """Browse latest papers by subject category."""
    from rich.table import Table

    console.print(
        Panel(
            f"[bold]Browsing:[/bold] {category} (page {page}) from {source}",
            title="PaperPilot",
            border_style="blue",
        )
    )

    if source == "xmol":
        from paperpilot.sources.xmol import XMolSource

        console.print(
            "[dim]Available categories: "
            + ", ".join(XMolSource.available_categories().keys())
            + "[/dim]\n"
        )

    src = _get_source(source)
    try:
        papers = src.browse(category=category, page=page)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not papers:
        console.print("[yellow]No papers found in this category.[/yellow]")
        return

    table = Table(title=f"{category.title()} - Latest Papers")
    table.add_column("#", style="bold", width=3)
    table.add_column("Title", max_width=60)
    table.add_column("Journal", max_width=25)
    table.add_column("Year", width=6)

    for i, p in enumerate(papers, 1):
        table.add_row(str(i), p.title, p.journal, p.year)

    console.print(table)
