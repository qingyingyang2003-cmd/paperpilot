"""Compare Agent — LLM-powered multi-paper comparison.

Takes multiple analyzed paper state dicts (from LangGraph) and produces
a structured comparison: a summary table with abbreviated fields for each
paper, plus a comprehensive analysis discussing similarities, differences,
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
from typing import Any

from paperpilot.agents.analyst import _create_llm
from paperpilot.config import config


def compare_papers(
    states: list[dict[str, Any]],
    language: str = "zh",
) -> dict[str, Any]:
    """Compare multiple papers using LLM.

    This is the main entry point, called by orchestrator.run_compare_workflow().

    Args:
        states: List of state dicts from LangGraph (already analyzed).
        language: Output language ("zh" or "en").

    Returns:
        Dict with keys: topic, generated_at, papers (list[dict]), analysis (str).
    """
    from rich.console import Console

    console = Console()

    # Step 1: Create LLM
    llm = _create_llm()
    console.print(f"  [dim]Provider: {config.llm.provider}, Model: {config.llm.model}[/dim]")

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


def compare_papers_fallback(states: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a comparison using only metadata (no LLM).

    Used when LLM is unavailable. Extracts raw fields from each
    state dict without abbreviation or analysis.
    """
    papers = []
    for state in states:
        metadata = state.get("metadata", {})
        authors = metadata.get("authors", [])
        first_author = authors[0].split()[-1] if authors else "Unknown"
        year = metadata.get("year", "")
        short_title = f"{first_author} {year}" if year else first_author

        methods = state.get("methods", "")
        results = state.get("results", "")
        innovations = state.get("innovations", "")
        limitations = state.get("limitations", "")

        papers.append(
            {
                "short_title": short_title,
                "year": year or "N/A",
                "research_question": state.get("research_question") or "（需要 LLM 分析）",
                "methods_brief": methods[:150] + "..." if len(methods) > 150 else methods or "N/A",
                "results_brief": results[:150] + "..." if len(results) > 150 else results or "N/A",
                "innovations_brief": innovations[:150] + "..."
                if len(innovations) > 150
                else innovations or "N/A",
                "limitations_brief": limitations[:150] + "..."
                if len(limitations) > 150
                else limitations or "N/A",
            }
        )

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
def _build_compare_prompt(states: list[dict[str, Any]], language: str) -> str:
    """Build the comparison prompt from multiple state dicts."""
    if language == "zh":
        lang_instruction = "请用中文输出。专业术语保留英文原文，首次出现时在括号中给出中文翻译。"
    else:
        lang_instruction = "Write the comparison in English."

    paper_blocks = []
    for i, state in enumerate(states, 1):
        metadata = state.get("metadata", {})
        block = f"""<paper_input index="{i}">
Title: {metadata.get("title", "")}
Authors: {", ".join(metadata.get("authors", []))}
Year: {metadata.get("year", "")}
Journal: {metadata.get("journal", "")}

Research Question: {state.get("research_question", "")}

Methods: {state.get("methods", "")}

Results: {state.get("results", "")}

Innovations: {state.get("innovations", "")}

Limitations: {state.get("limitations", "")}
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
    states: list[dict[str, Any]],
) -> dict[str, Any]:
    """Parse XML-tagged comparison response into a dict."""
    papers: list[dict[str, str]] = []

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
            metadata = state.get("metadata", {})
            authors = metadata.get("authors", [])
            first_author = authors[0].split()[-1] if authors else "Unknown"
            year = metadata.get("year", "")
            papers.append(
                {
                    "short_title": f"{first_author} {year}",
                    "year": year or "N/A",
                    "research_question": state.get("research_question", "N/A")[:100],
                    "methods_brief": state.get("methods", "N/A")[:100],
                    "results_brief": state.get("results", "N/A")[:100],
                    "innovations_brief": state.get("innovations", "N/A")[:100],
                    "limitations_brief": state.get("limitations", "N/A")[:100],
                }
            )

    analysis = _extract_field(content, "analysis")
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


def _derive_topic(states: list[dict[str, Any]]) -> str:
    """Derive a comparison topic from paper titles."""
    if not states:
        return "Paper Comparison"
    titles = [s.get("metadata", {}).get("title", "") for s in states]
    titles = [t for t in titles if t]
    if not titles:
        return "Paper Comparison"
    first = titles[0]
    if len(first) > 60:
        first = first[:57] + "..."
    return first
