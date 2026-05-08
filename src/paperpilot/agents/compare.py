"""Compare Agent — LLM-powered multi-paper comparison.

Takes multiple analyzed PaperState objects and produces a structured
comparison: a summary table with abbreviated fields for each paper,
plus a comprehensive analysis discussing similarities, differences,
and research trends.

Design decisions:
- Reuses _create_llm() from analyst.py (same factory, same config)
- XML output format with <paper index="N"> blocks + <analysis> block
- Each paper's fields are abbreviated to fit table cells (1-2 sentences)
- Graceful degradation: if LLM fails, returns raw metadata comparison
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from paperpilot.agents.analyst import _create_llm
from paperpilot.config import config

if TYPE_CHECKING:
    from paperpilot.orchestrator import PaperState


def compare_papers(
    states: list["PaperState"],
    language: str = "zh",
) -> dict[str, Any]:
    """Compare multiple papers using LLM.

    This is the main entry point, called by orchestrator.run_compare_workflow().

    Flow:
        1. Build a prompt containing each paper's key fields
        2. Ask LLM to generate abbreviated versions + comprehensive analysis
        3. Parse XML response into a dict matching comparison.md.j2 template

    Args:
        states: List of PaperState objects (already analyzed by Analyst Agent).
        language: Output language ("zh" or "en").

    Returns:
        Dict with keys: topic, generated_at, papers (list[dict]), analysis (str).
    """
    from rich.console import Console

    console = Console()

    # Step 1: Create LLM
    llm = _create_llm()
    console.print(
        f"  [dim]Provider: {config.llm.provider}, "
        f"Model: {config.llm.model}[/dim]"
    )

    # Step 2: Build prompt
    prompt = _build_compare_prompt(states, language)
    console.print(f"  [dim]Comparing {len(states)} papers[/dim]")

    # Step 3: Call LLM
    console.print("  [cyan]Generating comparison...[/cyan]")
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    # Step 4: Parse response
    result = _parse_compare_response(content, states)
    result["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    console.print("  [green]Comparison complete[/green]")
    return result


def compare_papers_fallback(states: list["PaperState"]) -> dict[str, Any]:
    """Generate a comparison using only metadata (no LLM).

    Used when LLM is unavailable. Extracts raw fields from each
    PaperState without abbreviation or analysis.
    """
    papers = []
    for state in states:
        first_author = state.metadata.authors[0].split()[-1] if state.metadata.authors else "Unknown"
        short_title = f"{first_author} {state.metadata.year}" if state.metadata.year else first_author

        papers.append({
            "short_title": short_title,
            "year": state.metadata.year or "N/A",
            "research_question": state.research_question or "（需要 LLM 分析）",
            "methods_brief": state.methods[:150] + "..." if len(state.methods) > 150 else state.methods or "N/A",
            "results_brief": state.results[:150] + "..." if len(state.results) > 150 else state.results or "N/A",
            "innovations_brief": state.innovations[:150] + "..." if len(state.innovations) > 150 else state.innovations or "N/A",
            "limitations_brief": state.limitations[:150] + "..." if len(state.limitations) > 150 else state.limitations or "N/A",
        })

    # Derive topic from common words in titles
    topic = _derive_topic(states)

    return {
        "topic": topic,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "papers": papers,
        "analysis": "",
    }


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def _build_compare_prompt(states: list["PaperState"], language: str) -> str:
    """Build the comparison prompt from multiple PaperState objects.

    Includes each paper's key fields and asks the LLM to:
    1. Generate abbreviated versions suitable for table cells
    2. Write a comprehensive analysis comparing all papers
    """
    if language == "zh":
        lang_instruction = (
            "请用中文输出。专业术语保留英文原文，"
            "首次出现时在括号中给出中文翻译。"
        )
    else:
        lang_instruction = "Write the comparison in English."

    # Build paper blocks
    paper_blocks = []
    for i, state in enumerate(states, 1):
        block = f"""<paper_input index="{i}">
Title: {state.metadata.title}
Authors: {', '.join(state.metadata.authors)}
Year: {state.metadata.year}
Journal: {state.metadata.journal}

Research Question: {state.research_question}

Methods: {state.methods}

Results: {state.results}

Innovations: {state.innovations}

Limitations: {state.limitations}
</paper_input>"""
        paper_blocks.append(block)

    papers_text = "\n\n".join(paper_blocks)

    prompt = f"""You are a scientific paper comparison assistant. You will compare {len(states)} research papers and produce a structured comparison.

{lang_instruction}

{papers_text}

Please produce the following output. Each paper MUST have its own <paper> block with the exact index matching the input.

For each paper, generate ABBREVIATED versions of each field — short enough to fit in a table cell (1-2 sentences max per field). Also generate a short_title in the format "LastName Year" (e.g., "Maddar 2019").

<output_format>
{_generate_paper_output_template(len(states))}

<analysis>
Write a comprehensive analysis (3-5 paragraphs) comparing these papers:
- What do they have in common? How do their approaches differ?
- What is the research trend or progression across these papers?
- Which paper makes the strongest contribution and why?
- What gaps remain? What would be a good next step for research?
</analysis>
</output_format>

IMPORTANT: Output ONLY the XML tags with content. Do not add text before or after."""

    return prompt


def _generate_paper_output_template(n: int) -> str:
    """Generate the XML template for N papers."""
    blocks = []
    for i in range(1, n + 1):
        blocks.append(f"""<paper index="{i}">
<short_title>LastName Year</short_title>
<year>Year</year>
<research_question>1-2 sentence abbreviated version</research_question>
<methods_brief>1-2 sentence abbreviated version</methods_brief>
<results_brief>1-2 sentence abbreviated version</results_brief>
<innovations_brief>1-2 sentence abbreviated version</innovations_brief>
<limitations_brief>1-2 sentence abbreviated version</limitations_brief>
</paper>""")
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
def _parse_compare_response(
    content: str,
    states: list["PaperState"],
) -> dict[str, Any]:
    """Parse XML-tagged comparison response into a dict.

    Extracts each <paper index="N"> block and the <analysis> block.
    Returns a dict matching the comparison.md.j2 template variables.
    """
    papers: list[dict[str, str]] = []

    # Extract each paper block
    paper_pattern = r'<paper\s+index="(\d+)">\s*(.*?)\s*</paper>'
    paper_matches = re.findall(paper_pattern, content, re.DOTALL)

    for _index, paper_content in paper_matches:
        paper = {
            "short_title": _extract_field(paper_content, "short_title"),
            "year": _extract_field(paper_content, "year"),
            "research_question": _extract_field(paper_content, "research_question"),
            "methods_brief": _extract_field(paper_content, "methods_brief"),
            "results_brief": _extract_field(paper_content, "results_brief"),
            "innovations_brief": _extract_field(paper_content, "innovations_brief"),
            "limitations_brief": _extract_field(paper_content, "limitations_brief"),
        }
        papers.append(paper)

    # If parsing failed, fall back to metadata
    if len(papers) < len(states):
        for i in range(len(papers), len(states)):
            state = states[i]
            first_author = state.metadata.authors[0].split()[-1] if state.metadata.authors else "Unknown"
            papers.append({
                "short_title": f"{first_author} {state.metadata.year}",
                "year": state.metadata.year or "N/A",
                "research_question": state.research_question[:100] if state.research_question else "N/A",
                "methods_brief": state.methods[:100] if state.methods else "N/A",
                "results_brief": state.results[:100] if state.results else "N/A",
                "innovations_brief": state.innovations[:100] if state.innovations else "N/A",
                "limitations_brief": state.limitations[:100] if state.limitations else "N/A",
            })

    # Extract analysis
    analysis = _extract_field(content, "analysis")

    # Derive topic
    topic = _derive_topic(states)

    return {
        "topic": topic,
        "papers": papers,
        "analysis": analysis,
    }


def _extract_field(content: str, tag: str) -> str:
    """Extract text between <tag> and </tag>."""
    pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def _derive_topic(states: list["PaperState"]) -> str:
    """Derive a comparison topic from paper titles.

    Takes the first paper's title as the topic base, truncated.
    """
    if not states:
        return "Paper Comparison"
    titles = [s.metadata.title for s in states if s.metadata.title]
    if not titles:
        return "Paper Comparison"
    # Use first title, truncated
    first = titles[0]
    if len(first) > 60:
        first = first[:57] + "..."
    return first
