# PaperPilot 📄✨

> 🧪 **丢一篇 PDF 进去，拿一份结构化笔记出来。** 让 AI 替你读论文——你负责思考，它负责整理。

[![CI](https://github.com/qingyingyang2003-cmd/paperpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/qingyingyang2003-cmd/paperpilot/actions) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

读论文最痛苦的不是读不懂，是读完记不住。PaperPilot 帮你把每篇论文变成一份**可搜索、可对比、格式统一**的笔记——总结、方法、结果、创新点、局限性，全部结构化。读过的论文自动进入本地知识库，下次搜关键词就能找到。

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

> 💡 **没有 API key 也能用。** 没配 key 时照样跑——输出元数据笔记（标题、作者、参考文献），不会崩溃。配了 key 才调 LLM 做深度分析。渐进式体验，不强制付费。

---

## 🎯 不只是一个 Prompt

这不是"把论文丢给 ChatGPT 然后复制粘贴"。PaperPilot 是一个完整的 pipeline：

```bash
# 一篇论文 → 结构化笔记
paperpilot read paper.pdf

# 三篇论文 → 对比表格 + 综合分析
paperpilot compare paper1.pdf paper2.pdf paper3.pdf

# 搜关键词 → 本地已读 + Semantic Scholar 200M 论文
paperpilot search "scanning ion conductance microscopy"

# 搜 + 下载 + 自动分析，一条命令搞定
paperpilot fetch "SICM surface charge" --download --analyze
```

像给你配了一个研究助理：*"把这几篇论文读了，整理成笔记，顺便帮我搜搜相关的。"*

---

## ✨ Features

| | Feature | 一句话说明 |
|---|---------|-----------|
| 📖 | **Single-paper analysis** | PDF → 8 段结构化 Markdown 笔记 |
| 📊 | **Multi-paper comparison** | 多篇论文并排对比，LLM 生成综合分析 |
| 🔍 | **Semantic search (RAG)** | 读过的论文自动入库，语义搜索秒找 |
| 📥 | **Paper fetch** | Semantic Scholar 搜索 + 下载 open-access PDF + 自动分析 |
| 📂 | **Category browsing** | 按学科浏览最新论文（x-mol） |
| 🖼️ | **Figure extraction** | 自动提取图片，嵌入笔记 |
| 🌐 | **Multi-provider** | Claude / GPT / DeepSeek，环境变量一键切换 |
| 🛡️ | **Never crashes** | 没 key 不崩、网络断不崩、PDF 解析失败不崩 |

---

## 🏗️ Architecture

> 💭 **为什么不直接调 API？** 因为论文分析是多步骤工作流——解析、分析、渲染、入库。LangGraph 的 StateGraph 让每一步都是独立的 node，可以单独测试、单独替换。conditional edge 让"有没有 API key"这种分支逻辑变成声明式的，而不是藏在 try/except 里。

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

**Read workflow 的 graph 结构：**

```
START → [parse] →─┬─ [analyze] ──────┐
                   │                  ├→ [render] → [index] → END
                   └─ [skip_analyze] ─┘
```

`parse` 之后有一个 **conditional edge**：检测到 API key → 走 `analyze`（LLM 深度分析）；没有 → 走 `skip_analyze`（优雅降级，输出元数据笔记）。

> 💭 **为什么 Parser 不用 LLM？** PDF 解析是确定性任务——同一个 PDF 每次解析结果应该一样。用 LLM 做这件事既慢又贵，还可能幻觉。能用 Tool 解决的不用 Agent，省钱又可靠。

---

## 🚀 Quick Start

```bash
# 1. Clone + install
git clone https://github.com/qingyingyang2003-cmd/paperpilot.git
cd paperpilot
uv sync          # or: pip install -e .

# 2. Set API key (optional — works without it)
export ANTHROPIC_API_KEY=sk-ant-xxx

# 3. Go
paperpilot read your-paper.pdf
```

<details>
<summary>🔀 切换 LLM 提供商</summary>

```bash
# OpenAI
export OPENAI_API_KEY=sk-xxx
export PAPERPILOT_PROVIDER=openai
export PAPERPILOT_MODEL=gpt-4o

# DeepSeek（便宜好用）
export DEEPSEEK_API_KEY=sk-xxx
export PAPERPILOT_PROVIDER=deepseek
export PAPERPILOT_MODEL=deepseek-chat
```

</details>

---

## 📝 Example Output

`paperpilot read nanoscale-surface-charge-hair.pdf` 生成的笔记长这样：

<details>
<summary>点击展开完整示例</summary>

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

---

## 🔧 How It Works

### Read：一篇论文 → 一份笔记

```
PDF ──→ [Parse] ──→ [Analyze] ──→ [Render] ──→ [Index]
         提取文本     LLM 分析      模板渲染      入向量库
         图片/元数据   8 个字段      Markdown      下次可搜
```

### Compare：多篇论文 → 对比表格

```
paper1.pdf ─┐
paper2.pdf ─┼→ 各自 Parse+Analyze → Compare Agent → 对比表格 + 综合分析
paper3.pdf ─┘
```

### Search：关键词 → 找论文

```
"SICM surface charge"
    ├→ Semantic Scholar（外部 200M+ 论文）
    └→ ChromaDB（本地已读论文）
         → 按 DOI 去重 → 展示结果
```

---

## 🛠️ Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Orchestration** | LangGraph | StateGraph + conditional routing，不是玩具调用链 |
| **LLM** | Claude + GPT + DeepSeek | 200K context 吃得下长论文，多 provider 可切换 |
| **PDF** | PyMuPDF | C 底层，快，文本+图片+元数据一把梭 |
| **Vector store** | ChromaDB | 本地零配置，自带 embedding，不用调外部 API |
| **CLI** | Typer + Rich | 类型注解驱动，终端输出好看 |
| **Templates** | Jinja2 | 笔记格式可自定义，不硬编码 |
| **Package** | uv | 比 pip 快 100 倍，一个工具管所有 |
| **Testing** | pytest | 83 个测试，不调真实 API 也能跑 |
| **Evaluation** | LLM-as-Judge | 四维度评分 + 自动化报告 |

---

## 📁 Project Structure

```
paperpilot/
├── src/paperpilot/
│   ├── cli.py              # 用户入口：read / compare / search / fetch / browse
│   ├── orchestrator.py     # LangGraph StateGraph（5 nodes + conditional edge）
│   ├── config.py           # 配置管理（env var override）
│   ├── agents/
│   │   ├── analyst.py      # Analyst Agent：XML structured output + 解析
│   │   └── compare.py      # Compare Agent：多篇对比 + fallback
│   ├── sources/
│   │   ├── semantic_scholar.py  # Semantic Scholar API（免费，200M+ 论文）
│   │   └── xmol.py         # x-mol.com 爬虫（cookie auth）
│   ├── tools/
│   │   ├── pdf_tools.py    # PyMuPDF：文本/元数据/图片/参考文献
│   │   ├── figure_tools.py # 图表管理
│   │   └── template_tools.py  # Jinja2 渲染
│   └── store/
│       └── vector_store.py # ChromaDB 封装：入库/搜索/去重
├── tests/                  # 83 tests, all passing
├── eval/                   # LLM-as-Judge quality evaluation
├── docs/                   # 架构文档 + 设计决策记录
└── examples/               # 示例输出
```

---

## 🧑‍💻 Development

```bash
uv sync                              # 安装依赖
make test                            # 跑测试（不需要网络和 API key）
make lint                            # 代码检查
make format                          # 自动格式化
uv run pytest --run-network          # 跑网络测试（会调真实 API）
```

---

## 📊 Evaluation

PaperPilot 内置了 LLM-as-Judge 评估系统，对生成的笔记做四维度打分：

```bash
uv run python eval/eval.py examples/output/*.md --summary
```

| Dimension | Avg Score | 说明 |
|-----------|-----------|------|
| Completeness | 24.0/25 | 所有字段完整填充 |
| Specificity | 24.6/25 | 定量数据精确 |
| Clarity | 23.0/25 | 逻辑清晰、术语解释到位 |
| Insight | 22.0/25 | 深度分析（最弱项，持续优化中） |

> 已知局限：同模型自评存在 bias，绝对分数偏高。详见 [`eval/README.md`](eval/README.md)。

---

## 🗺️ Roadmap

- [x] Phase 1: 项目骨架 + PDF 工具 + CLI
- [x] Phase 1.5: 论文源（Semantic Scholar + x-mol）
- [x] Phase 2: Analyst Agent（LLM 接入）
- [x] Phase 3: Compare Agent + Search Agent + RAG
- [x] Phase 4: README, examples, CI
- [x] Phase 5: LangGraph StateGraph 重构
- [x] Phase 5.5: 质量评估系统（LLM-as-Judge）
- [ ] Phase 6: 多篇论文异步并行处理
- [ ] Phase 7: `paperpilot config` 持久化配置
- [ ] Phase 8: Cross-model evaluation + human baseline

---

## 📄 License

MIT

---

<p align="center">
  <i>为不想读论文但必须读论文的人而做。 🌙</i>
</p>
