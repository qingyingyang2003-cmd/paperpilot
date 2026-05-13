# PaperPilot 📄✨

> 🧪 **PDF in, structured notes out.** Let AI read your papers — wake up to organized, searchable research notes.

[![CI](https://github.com/qingyingyang2003-cmd/paperpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/qingyingyang2003-cmd/paperpilot/actions) [![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

PaperPilot 是一个 AI 驱动的科研论文分析 Agent。输入一篇 PDF，自动输出结构化笔记：一段话总结、摘要翻译、研究框架、方法、结果、创新点、局限性，以及值得追踪的参考文献。

```bash
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

## 🎯 Features

| Feature | Command | Description |
|---------|---------|-------------|
| 📖 Single-paper analysis | `paperpilot read paper.pdf` | PDF → structured Markdown note (8 sections) |
| 📊 Multi-paper comparison | `paperpilot compare a.pdf b.pdf` | Side-by-side comparison table + comprehensive analysis |
| 🔍 Semantic search (RAG) | `paperpilot search "keyword"` | Search local library (ChromaDB) + Semantic Scholar |
| 📥 Paper fetch | `paperpilot fetch "topic" --download` | Find + download open-access PDFs + auto-analyze |
| 📂 Category browsing | `paperpilot browse chemistry` | Browse latest papers by subject (x-mol) |
| 🖼️ Figure extraction | `--figures` (default on) | Pull images from PDFs, embed in notes |
| 🌐 Multi-provider LLM | `PAPERPILOT_PROVIDER=openai` | Claude / GPT / DeepSeek, switch via env var |
| 🛡️ Graceful degradation | — | Works without API key (metadata-only notes), never crashes |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLI Layer                          Typer + Rich        │
├─────────────────────────────────────────────────────────┤
│  Orchestrator Layer                 LangGraph StateGraph│
├─────────────────────────────────────────────────────────┤
│  Agent Layer          Parser / Analyst / Compare        │
├─────────────────────────────────────────────────────────┤
│  Tools Layer          PDF / Templates / Search APIs     │
└─────────────────────────────────────────────────────────┘
```

The orchestrator is a **compiled LangGraph `StateGraph`** with conditional routing:

```
START → [parse] →─┬─ [analyze] ──────┐
                   │                  ├→ [render] → [index] → END
                   └─ [skip_analyze] ─┘
```

- **Conditional edge**: after `parse`, checks if LLM API key is configured
- **If yes** → full LLM analysis (Claude/GPT)
- **If no** → graceful fallback (metadata-only notes)

<details>
<summary>📐 Design Principles</summary>

- **Graceful degradation** — every component has a fallback. No API key? Metadata-only notes. API error? Partial results. PDF parsing fails? Heuristic fallback.
- **Local first** — all data stays on your machine. Only LLM API calls send text externally.
- **Tools vs Agents** — deterministic work (PDF parsing, file I/O) uses Tools. Only understanding and analysis uses LLM-powered Agents. This saves cost and improves reliability.
- **Template-driven** — note format is a Jinja2 template, not hardcoded. Customize it for your field.

</details>

---

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- An Anthropic or OpenAI API key (optional — works without one, just no LLM analysis)

### Install

```bash
git clone https://github.com/qingyingyang2003-cmd/paperpilot.git
cd paperpilot
uv sync          # or: pip install -e .
```

### Set up API key

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-xxx

# Or OpenAI
export OPENAI_API_KEY=sk-xxx

# Or DeepSeek
export DEEPSEEK_API_KEY=sk-xxx
export PAPERPILOT_PROVIDER=deepseek
export PAPERPILOT_MODEL=deepseek-chat
```

### Usage

```bash
# Analyze a paper
paperpilot read paper.pdf

# Specify output directory and language
paperpilot read paper.pdf -o ./notes --lang en

# Compare multiple papers
paperpilot compare paper1.pdf paper2.pdf paper3.pdf -o comparison.md

# Search papers (Semantic Scholar + local library)
paperpilot search "scanning ion conductance microscopy"

# Fetch + download + auto-analyze
paperpilot fetch "SICM surface charge" --download --analyze

# Browse latest papers by category
paperpilot browse chemistry --source xmol
```

---

## 📝 Example Output

Running `paperpilot read nanoscale-surface-charge-hair.pdf` produces:

<details>
<summary>Click to expand sample note</summary>

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

## 创新点
- 首次实现头发表面电荷的纳米级定量成像
- SICM 在液相中工作，避免了 KPFM 的湿度问题
- 同步获取形貌+电荷

## 局限性
- 只测了一位供体的头发，样本代表性有限
- FEM 模型假设平面基底
- 扫描区域较小（~10×10 μm）

## 值得追踪的参考文献
- Perry et al., JACS 2016 — SICM 形貌+电荷同步测量
- Kang et al., ACS Nano 2017 — hopping mode 速度提升
- Page et al., Anal. Chem. 2016 — potential-pulse 方法
```

</details>

See [examples/](examples/) for full sample outputs.

---

## 🔧 How It Works

### The Read Pipeline

```
paperpilot read paper.pdf
        │
        ▼
   ┌─────────┐     Deterministic (no LLM)
   │  Parse  │──→  Extract text, metadata, figures, references (PyMuPDF)
   └────┬────┘
        │
        ▼ ← conditional edge (API key available?)
   ┌─────────┐     LLM-powered
   │ Analyze │──→  Claude/GPT generates: summary, methods, results,
   └────┬────┘     innovations, limitations, key references
        │
        ▼
   ┌─────────┐     Deterministic
   │ Render  │──→  Jinja2 template + analysis → Markdown note
   └────┬────┘
        │
        ▼
   ┌─────────┐     Background
   │  Index  │──→  Auto-index into ChromaDB for future search
   └─────────┘
```

### The Compare Pipeline

```
paperpilot compare a.pdf b.pdf c.pdf
        │
        ▼
   Parse + Analyze each paper (reuses read graph)
        │
        ▼
   Compare Agent (LLM generates side-by-side table + analysis)
        │
        ▼
   Jinja2 comparison template → Markdown table
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
         Deduplicate by DOI → Display results
```

---

## 🛠️ Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Orchestration** | LangGraph | StateGraph with conditional routing for workflow control |
| **LLM** | Claude + OpenAI + DeepSeek | Claude's 200K context fits long papers; multi-provider support |
| **PDF parsing** | PyMuPDF (fitz) | Fast C-based extraction: text, images, metadata |
| **Vector store** | ChromaDB | Local, zero-config, built-in embeddings (all-MiniLM-L6-v2) |
| **CLI** | Typer + Rich | Type-annotated CLI with colored terminal output |
| **Templates** | Jinja2 | Mature, flexible, same engine as Flask/Django |
| **HTTP** | httpx | Modern async-capable HTTP client |
| **Package manager** | uv | 100x faster than pip, manages Python + venv + deps |
| **Testing** | pytest | 83 tests, all passing |

---

## 📁 Project Structure

```
paperpilot/
├── src/paperpilot/
│   ├── cli.py              # CLI commands (read, compare, search, fetch, browse)
│   ├── config.py           # Configuration (API keys, models, paths)
│   ├── orchestrator.py     # LangGraph StateGraph + PaperState TypedDict
│   ├── agents/
│   │   ├── analyst.py      # LLM-powered paper analysis (XML structured output)
│   │   └── compare.py      # LLM-powered multi-paper comparison
│   ├── sources/
│   │   ├── __init__.py     # PaperSource ABC + PaperInfo dataclass
│   │   ├── semantic_scholar.py  # Semantic Scholar API (free, 200M+ papers)
│   │   └── xmol.py         # x-mol.com scraper (cookie auth)
│   ├── tools/
│   │   ├── pdf_tools.py    # PDF text/metadata/figure/reference extraction
│   │   ├── figure_tools.py # Figure management and markdown embedding
│   │   └── template_tools.py  # Jinja2 template rendering
│   └── store/
│       └── vector_store.py # ChromaDB vector store for RAG search
├── tests/                  # 83 tests (all passing)
├── docs/                   # Architecture + design decision docs
└── examples/               # Sample outputs
```

---

## 🧑‍💻 Development

```bash
# Install dev dependencies
uv sync

# Run tests (no network, no API key needed)
uv run pytest -v -k "not network"

# Run all tests including network
uv run pytest --run-network
```

---

## 🗺️ Roadmap

- [x] Phase 1: Project scaffold + PDF tools + CLI
- [x] Phase 1.5: Paper sources (Semantic Scholar + x-mol)
- [x] Phase 2: Analyst Agent (LLM integration)
- [x] Phase 3: Compare Agent + Search Agent + RAG (ChromaDB)
- [x] Phase 4: README, examples, CI
- [x] Phase 5: LangGraph StateGraph refactor + code review
- [ ] Phase 6: Async parallel processing for multi-paper workflows
- [ ] Phase 7: `paperpilot config` command + `.env` support

---

## 📄 License

MIT

---

<p align="center">
  <i>Built for researchers who'd rather think than read. 🧠</i>
</p>
