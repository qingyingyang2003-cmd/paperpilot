# PaperPilot Evaluation

LLM-as-Judge evaluation for generated paper notes.

## Usage

```bash
# Evaluate a single note
uv run python eval/eval.py examples/output/highspeed-sicm-for-the.md

# Batch evaluate with summary
uv run python eval/eval.py examples/output/*.md --summary
```

## Scoring Rubric

Four dimensions, 25 points each (100 total):

| Dimension | What it measures |
|-----------|-----------------|
| **Completeness** | All sections present with substantive content |
| **Specificity** | Quantitative detail, concrete parameters, precise language |
| **Clarity** | Logical flow, term definitions, readability |
| **Insight** | Genuine analysis beyond surface extraction |

Grade thresholds: Excellent (85+), Good (70+), Acceptable (55+), Poor (<55)

## Methodology

- **Evaluator:** Same LLM provider used for note generation (default: Claude)
- **Approach:** Single-pass scoring with structured XML output
- **Rubric:** Defined in `rubric.json`, includes calibration guidelines

## Known Limitations

1. **Self-evaluation bias:** Using the same model family for generation and evaluation inflates scores. Our notes consistently score 90+, which likely reflects this bias rather than true quality.
2. **No ground truth:** Without human-annotated reference notes, we cannot compute precision/recall of extracted information.
3. **Single evaluator:** No inter-rater reliability. A more robust approach would use multiple models or human reviewers.

## How to interpret results

The absolute scores are less meaningful than:
- **Relative ranking** between notes (which papers produce better notes?)
- **Per-dimension breakdown** (is the system consistently weak on insight vs. completeness?)
- **Specific feedback** in each report (actionable improvement suggestions)

## Future improvements

- Cross-model evaluation (generate with Claude, evaluate with GPT, or vice versa)
- Human annotation of 3-5 notes as ground truth
- Automated regression testing: re-evaluate after prompt changes to detect quality drift
