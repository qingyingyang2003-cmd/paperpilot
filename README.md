# PaperPilot

AI-powered scientific paper analysis agent. Read a PDF, get structured notes — from your terminal.

PaperPilot 是一个 AI 驱动的科研论文分析工具。输入一篇 PDF，自动输出结构化笔记：一段话总结、摘要翻译、研究框架、方法、结果、创新点、局限性，以及值得追踪的参考文献。

```
paperpilot read paper.pdf
```

```
Analyzing: paper.pdf
 ━━━━━━━━━━━━━━━━━━━━ 100%  Extracted 12 figures
 Provider: anthropic, Model: claude-sonnet-4-20250514
 Calling LLM...
 Analysis complete

Done! Note saved to: ./notes/nanoscale-surface-charge-hair.md
```

---

## Features

- **Single-paper analysis** — PDF in, structured Markdown note out (8 sections)
- **Multi-paper comparison** — compare 2+ papers side-by-side with LLM-generated analysis table
- **LLM-powered** — Claude or GPT reads the paper and generates analysis in Chinese or English
- **Semantic search (RAG)** — analyzed papers auto-index into ChromaDB; search across your local library + Semantic Scholar in one command
- **Paper search** — find papers via Semantic Scholar API (free, no key needed)
- **Paper fetch** — search + download open-access PDFs + auto-analyze
- **Category browsing** — browse latest papers on x-mol.com by subject
- **Figure extraction** — pull images from PDFs, embed in notes
- **Template-driven** — customize note format with Jinja2 templates
- **Graceful degradation** — works without API key (metadata-only notes), never crashes

## Architecture

```
┌─────────────────────────────┐
│        CLI Layer            │  Typer + Rich
├─────────────────────────────┤
│     Orchestrator Layer      │  LangGraph StateGraph
├─────────────────────────────┤
│       Agent Layer           │  Parser / Analyst / Compare / Search
├─────────────────────────────┤
│       Tools Layer           │  PDF parsing / templates / search APIs
└─────────────────────────────┘
```

Four layers, each depends only on the layer below. Tools are deterministic functions (no LLM). Agents add intelligence on top. The orchestrator uses a LangGraph `StateGraph` with conditional routing — nodes receive a shared `PaperState` TypedDict and return partial updates.

See [docs/architecture.md](docs/architecture.md) for the full design document.

---

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- An Anthropic or OpenAI API key (optional — works without one, just no LLM analysis)

### Install

```bash
# Clone
git clone https://github.com/qingyingyang200-cmd/paperpilot.git
cd paperpilot

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Set up API key

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-xxx

# Or OpenAI
export OPENAI_API_KEY=sk-xxx
```

### Usage

```bash
# Analyze a paper — generates structured notes
paperpilot read paper.pdf

# Specify output directory and language
paperpilot read paper.pdf -o ./notes --lang en

# Compare multiple papers — generates comparison table
paperpilot compare paper1.pdf paper2.pdf paper3.pdf -o comparison.md

# Search papers (Semantic Scholar + local library)
paperpilot search "scanning ion conductance microscopy"

# Fetch papers from Semantic Scholar
paperpilot fetch "SICM surface charge" -n 5

# Search + download open-access PDFs
paperpilot fetch "SICM surface charge" --download -o ./papers

# Search + download + auto-analyze
paperpilot fetch "SICM hair" --download --analyze

# Browse latest papers by category (requires x-mol cookie)
paperpilot browse chemistry --source xmol
```

---

## Example Output

Running `paperpilot read nanoscale-surface-charge-hair.pdf` produces a note like this:

```markdown
# Nanoscale Surface Charge Visualization of Human Hair
- 作者：Faduma M. Maddar, David Perry, Patrick R. Unwin
- 期刊/会议：Analytical Chemistry
- 年份：2019
- DOI：10.1021/acs.analchem.8b05977

## 一段话总结
本文首次使用 SICM（扫描离子电导显微镜）结合 FEM（有限元模拟）实现了
人类头发表面电荷密度的纳米级定量可视化。通过 hopping mode 配合电位脉冲
计时电流法，在液相环境中同步获取形貌和电荷信息...

## 方法
SICM hopping mode + potential-pulse chronoamperometry，每个像素点
同时获取形貌和电荷信息。通过 COMSOL Multiphysics 进行有限元模拟...

### 关键实验参数
- Probe aperture：~220 nm
- Electrolyte：50 mM KCl
- Scan mode：Hopping mode
- Setpoint：3% current drop

## 关键结果
1. 未处理头发：表面电荷密度约 -15 mC/m²
2. 漂白处理后：电荷增至 -100 mC/m²
3. 护发素处理后：电荷从负转正约 +5 mC/m²

...
```

See [examples/](examples/) for full sample outputs.

---

## How It Works

### The Read Pipeline

```
paperpilot read paper.pdf
        │
        ▼
┌─────────────────────────────────────────────────┐
│  LangGraph StateGraph (compiled, reusable)      │
│                                                 │
│  START → [parse] → ─┬─ [analyze] ──┐           │
│                      │              ├→ [render]  │
│                      └─ [skip] ─────┘     │     │
│                                       [index]   │
│                                           │     │
│                                          END    │
└─────────────────────────────────────────────────┘
        │
        ▼
   ./notes/paper-title.md
```

The conditional edge after `parse` checks if an LLM API key is configured. If yes, route to `analyze` (full LLM analysis). If no, route to `skip_analyze` (graceful degradation with metadata-only notes).

### The Compare Pipeline

```
paperpilot compare a.pdf b.pdf c.pdf
        │
        ▼
   ┌──────────────┐
   │ Parse + Analyze each paper individually
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │ Compare Agent │  LLM compares all papers side-by-side
   └──────┬───────┘   Generates abbreviated fields + comprehensive analysis
          │
          ▼
   ┌──────────────┐
   │ Render Table │  Jinja2 comparison template → Markdown table
   └──────────────┘
```

### The Search Pipeline

```
paperpilot search "SICM surface charge"
        │
        ├──────────────────────┐
        ▼                      ▼
   Semantic Scholar       ChromaDB (local)
   200M+ papers           Your analyzed papers
        │                      │
        └──────────┬───────────┘
                   ▼
            Deduplicate by DOI
            Display results
```

### Paper Sources

| Source | Auth | Features |
|--------|------|----------|
| **Semantic Scholar** | None (free API) | Search 200M+ papers, open-access PDF links, Unpaywall fallback |
| **x-mol.com** | Cookie | Search + browse by category, Chinese academic content |

### Design Principles

- **Graceful degradation** — every component has a fallback. No API key? Metadata-only notes. API error? Partial results. PDF parsing fails? Heuristic fallback.
- **Local first** — all data stays on your machine. Only LLM API calls send text externally.
- **Tools vs Agents** — deterministic work (PDF parsing, file I/O) uses Tools. Only understanding and analysis uses LLM-powered Agents. This saves cost and improves reliability.
- **Template-driven** — note format is a Jinja2 template, not hardcoded. Customize it for your field.

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Vector store | ChromaDB | Local, zero-config, built-in embeddings (all-MiniLM-L6-v2) |
| LLM | Claude (Anthropic) + OpenAI | Claude's 200K context fits long papers; OpenAI as alternative |
| LLM framework | LangGraph + LangChain | StateGraph for workflow orchestration with conditional routing; LangChain for LLM abstraction |
| PDF parsing | PyMuPDF (fitz) | Fast C-based extraction: text, images, metadata |
| CLI | Typer + Rich | Type-annotated CLI with colored terminal output |
| Templates | Jinja2 | Mature, flexible, same engine as Flask/Django |
| HTTP | httpx | Modern async-capable HTTP client |
| HTML parsing | BeautifulSoup4 | For x-mol web scraping |
| Package manager | uv | 100x faster than pip, manages Python + venv + deps |
| Testing | pytest | Python community standard |

---

## Project Structure

```
paperpilot/
├── src/paperpilot/
│   ├── cli.py              # CLI commands: read, fetch, browse, search, compare
│   ├── config.py           # Configuration (API keys, models, paths)
│   ├── orchestrator.py     # LangGraph StateGraph workflows + PaperState
│   ├── agents/
│   │   ├── analyst.py      # LLM-powered paper analysis
│   │   └── compare.py      # LLM-powered multi-paper comparison
│   ├── sources/
│   │   ├── __init__.py     # PaperSource ABC + PaperInfo dataclass
│   │   ├── semantic_scholar.py  # Semantic Scholar API (free)
│   │   └── xmol.py         # x-mol.com scraper (cookie auth)
│   ├── tools/
│   │   ├── pdf_tools.py    # PDF text/metadata/figure/reference extraction
│   │   ├── figure_tools.py # Figure management and markdown embedding
│   │   └── template_tools.py  # Jinja2 template rendering
│   ├── store/
│   │   └── vector_store.py # ChromaDB vector store for RAG search
│   └── templates/
│       ├── paper_note.md.j2     # Single paper note template
│       └── comparison.md.j2     # Multi-paper comparison template
├── tests/                  # 83 tests (all passing)
├── docs/
│   ├── architecture.md     # Full architecture design document
│   ├── phase2-analyst-agent.md  # Analyst Agent design decisions
│   └── phase3-compare-rag.md   # Compare Agent + RAG design decisions
└── examples/               # Sample outputs
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run only local tests (no network, no API key needed)
uv run pytest -v -k "not network"

# Run network tests (hits real APIs)
uv run pytest --run-network
```

## Roadmap

- [x] Phase 1: Project scaffold + PDF tools + CLI
- [x] Phase 1.5: Paper sources (Semantic Scholar + x-mol)
- [x] Phase 2: Analyst Agent (LLM integration)
- [x] Phase 3: Compare Agent + Search Agent + RAG (ChromaDB)
- [x] Phase 4: README, examples, CI

---

## License

MIT
