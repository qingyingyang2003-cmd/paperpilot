"""PaperPilot Note Quality Evaluator — LLM-as-Judge.

Evaluates generated paper notes against a scoring rubric.
Uses the same LLM provider configured for PaperPilot.

Usage:
    python eval/eval.py examples/output/highspeed-sicm-for-the.md
    python eval/eval.py examples/output/*.md          # Batch evaluate
    python eval/eval.py examples/output/*.md --summary  # Summary only
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path so we can import paperpilot
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from paperpilot.agents.analyst import _create_llm, _extract_tag

RUBRIC_PATH = Path(__file__).parent / "rubric.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def load_rubric() -> dict:
    """Load the evaluation rubric."""
    return json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))


def build_eval_prompt(note_content: str, rubric: dict) -> str:
    """Build the evaluation prompt for LLM-as-judge."""
    dimensions_text = ""
    for dim in rubric["dimensions"]:
        criteria_list = "\n".join(f"    - {c}" for c in dim["criteria"])
        dimensions_text += f"""
  {dim['name']} ({dim['weight']} points): {dim['description']}
  Criteria:
{criteria_list}
"""

    return f"""You are an expert evaluator for AI-generated scientific paper notes.
Your job is to score a note against a rubric and provide actionable feedback.

## Scoring Rubric
{dimensions_text}

## Note to Evaluate

{note_content}

## Instructions

Score each dimension from 0 to 25. Be strict but fair — a score of 20+ means genuinely excellent work.

Scoring calibration:
- 22-25: Exceptional. Could be used as-is in a literature review or thesis.
- 18-21: Good. Substantive and useful, with minor gaps.
- 14-17: Acceptable. Covers the basics but lacks depth or precision.
- 10-13: Below average. Missing key information or contains vague statements.
- 0-9: Poor. Mostly stubs, placeholders, or incorrect information.

Be critical. Most AI-generated notes score 15-20, not 23-25. Deduct points for:
- Vague language where specifics are possible
- Sections that merely restate the abstract
- Innovations that don't clearly distinguish from prior work
- Limitations that are generic rather than paper-specific

Output your evaluation in the following XML format:

<completeness_score>NUMBER</completeness_score>
<completeness_feedback>Brief explanation of score, citing specific examples from the note.</completeness_feedback>

<specificity_score>NUMBER</specificity_score>
<specificity_feedback>Brief explanation.</specificity_feedback>

<clarity_score>NUMBER</clarity_score>
<clarity_feedback>Brief explanation.</clarity_feedback>

<insight_score>NUMBER</insight_score>
<insight_feedback>Brief explanation.</insight_feedback>

<strengths>2-3 bullet points of what this note does well.</strengths>

<weaknesses>2-3 bullet points of what could be improved.</weaknesses>

<suggestions>1-3 specific, actionable suggestions for improvement.</suggestions>

IMPORTANT: Output ONLY the XML tags. No text before or after."""


def evaluate_note(note_path: Path) -> dict:
    """Evaluate a single note file and return structured results."""
    rubric = load_rubric()
    note_content = note_path.read_text(encoding="utf-8")

    # Extract title from first line
    first_line = note_content.split("\n")[0]
    title = first_line.lstrip("# ").strip()

    # Call LLM
    llm = _create_llm()
    prompt = build_eval_prompt(note_content, rubric)
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    # Parse scores
    scores = {}
    feedback = {}
    for dim in rubric["dimensions"]:
        name = dim["name"]
        score_str = _extract_tag(content, f"{name}_score")
        try:
            scores[name] = min(25, max(0, int(score_str.strip())))
        except (ValueError, AttributeError):
            scores[name] = 0
        feedback[name] = _extract_tag(content, f"{name}_feedback")

    total = sum(scores.values())

    # Determine grade
    thresholds = rubric["scoring"]["thresholds"]
    if total >= thresholds["excellent"]:
        grade = "Excellent"
    elif total >= thresholds["good"]:
        grade = "Good"
    elif total >= thresholds["acceptable"]:
        grade = "Acceptable"
    else:
        grade = "Poor"

    return {
        "title": title,
        "file": note_path.name,
        "scores": scores,
        "total": total,
        "grade": grade,
        "feedback": feedback,
        "strengths": _extract_tag(content, "strengths"),
        "weaknesses": _extract_tag(content, "weaknesses"),
        "suggestions": _extract_tag(content, "suggestions"),
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def render_report(result: dict) -> str:
    """Render evaluation result as markdown report."""
    scores = result["scores"]
    feedback = result["feedback"]

    score_lines = ""
    for name, score in scores.items():
        pct = int(score / 25 * 100)
        bar = "█" * (score // 2) + "░" * ((25 - score) // 2)
        score_lines += f"| {name.capitalize():<13} | {score}/25 | {bar} | {pct}% |\n"

    report = f"""# Evaluation Report: {result['title']}

**File:** `{result['file']}`
**Score:** {result['total']}/100 ({result['grade']})
**Evaluated:** {result['evaluated_at']}

## Dimension Scores

| Dimension     | Score | Visual | Pct |
|---------------|-------|--------|-----|
{score_lines}
## Feedback

### Completeness ({scores['completeness']}/25)
{feedback.get('completeness', 'N/A')}

### Specificity ({scores['specificity']}/25)
{feedback.get('specificity', 'N/A')}

### Clarity ({scores['clarity']}/25)
{feedback.get('clarity', 'N/A')}

### Insight ({scores['insight']}/25)
{feedback.get('insight', 'N/A')}

## Strengths
{result['strengths']}

## Weaknesses
{result['weaknesses']}

## Suggestions
{result['suggestions']}
"""
    return report


def render_summary(results: list[dict]) -> str:
    """Render a summary table for multiple evaluations."""
    lines = ["# PaperPilot Evaluation Summary\n"]
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**Papers evaluated:** {len(results)}\n")

    # Summary table
    lines.append("| Paper | Score | Grade | Completeness | Specificity | Clarity | Insight |")
    lines.append("|-------|-------|-------|:---:|:---:|:---:|:---:|")
    for r in results:
        s = r["scores"]
        short_title = r["title"][:40] + "..." if len(r["title"]) > 40 else r["title"]
        lines.append(
            f"| {short_title} | **{r['total']}** | {r['grade']} "
            f"| {s['completeness']} | {s['specificity']} | {s['clarity']} | {s['insight']} |"
        )

    # Averages
    avg_total = sum(r["total"] for r in results) / len(results)
    lines.append(f"\n**Average score:** {avg_total:.1f}/100\n")

    # Common patterns
    lines.append("## Observations\n")
    high = max(results, key=lambda r: r["total"])
    low = min(results, key=lambda r: r["total"])
    lines.append(f"- Highest: {high['title'][:50]} ({high['total']}/100)")
    lines.append(f"- Lowest: {low['title'][:50]} ({low['total']}/100)")

    dim_avgs = {}
    for dim in ["completeness", "specificity", "clarity", "insight"]:
        dim_avgs[dim] = sum(r["scores"][dim] for r in results) / len(results)
    weakest = min(dim_avgs, key=dim_avgs.get)
    strongest = max(dim_avgs, key=dim_avgs.get)
    lines.append(f"- Strongest dimension: {strongest} (avg {dim_avgs[strongest]:.1f}/25)")
    lines.append(f"- Weakest dimension: {weakest} (avg {dim_avgs[weakest]:.1f}/25)")

    return "\n".join(lines)


def main() -> None:
    """CLI entry point."""
    import glob

    if len(sys.argv) < 2:
        print("Usage: python eval/eval.py <note.md> [note2.md ...] [--summary]")
        print("       python eval/eval.py examples/output/*.md --summary")
        sys.exit(1)

    summary_mode = "--summary" in sys.argv
    paths = [Path(p) for p in sys.argv[1:] if not p.startswith("--")]

    # Expand globs on Windows
    expanded: list[Path] = []
    for p in paths:
        if "*" in str(p):
            expanded.extend(Path(f) for f in glob.glob(str(p)))
        else:
            expanded.append(p)
    paths = [p for p in expanded if p.exists() and p.suffix == ".md"]

    if not paths:
        print("No valid .md files found.")
        sys.exit(1)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for i, note_path in enumerate(paths, 1):
        print(f"\n[{i}/{len(paths)}] Evaluating: {note_path.name}")
        try:
            result = evaluate_note(note_path)
            results.append(result)
            print(f"  Score: {result['total']}/100 ({result['grade']})")

            # Save individual report
            report = render_report(result)
            report_path = REPORTS_DIR / f"eval-{note_path.stem}.md"
            report_path.write_text(report, encoding="utf-8")
            print(f"  Report: {report_path}")
        except Exception as e:
            print(f"  Error: {e}")

    # Generate summary
    if results and (summary_mode or len(results) > 1):
        summary = render_summary(results)
        summary_path = REPORTS_DIR / "summary.md"
        summary_path.write_text(summary, encoding="utf-8")
        print(f"\nSummary saved to: {summary_path}")
        print(f"\nOverall average: {sum(r['total'] for r in results) / len(results):.1f}/100")


if __name__ == "__main__":
    main()
