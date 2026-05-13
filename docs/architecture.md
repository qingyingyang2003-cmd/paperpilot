aperpilot/tools/template_tools.py
/mnt/d/paperpilot/tests/__init__.py
/mnt/d/paperpilot/tests/test_analyst.py
/mnt/d/paperpilot/tests/test_compare.py
/mnt/d/paperpilot/tests/test_pdf_tools.py
/mnt/d/paperpilot/tests/test_sources.py
/mnt/d/paperpilot/tests/test_template_tools.py
/mnt/d/paperpilot/tests/test_vector_store.py

● Read(/mnt/d/paperpilot/README.md)
Read 320 lines

● Read(/mnt/d/paperpilot/pyproject.toml)
Read 43 lines# PaperPilot 架构设计与搭建文档

## 项目定位

PaperPilot 是一个 AI 驱动的科研论文分析 Agent 工具。用户输入一篇 PDF 论文，PaperPilot 自动完成解析、分析、生成结构化笔记、多篇对比、文献检索等工作。

它不是一个玩具 demo，而是从真实科研场景出发的工具——作者本人就是每天在用它读论文的研究生。

---

## 一、设计原则

### 1. 分层架构（Layered Architecture）

整个项目分为四层，每层只依赖下一层，不跨层调用：

```
┌─────────────────────────────┐
│        CLI Layer            │  ← 用户交互（Typer + Rich）
├─────────────────────────────┤
│     Orchestrator Layer      │  ← 工作流编排（LangGraph 状态机）
├─────────────────────────────┤
│       Agent Layer           │  ← 智能体（Parser / Analyst / Compare / Search）
├─────────────────────────────┤
│       Tools Layer           │  ← 底层工具函数（PDF 解析 / 图表提取 / 模板渲染 / 搜索）
└─────────────────────────────┘
```

**为什么这样分？**

- **可测试性**：Tools 层是纯函数，不依赖 LLM，可以用 pytest 直接测试
- **可替换性**：想换 LLM 提供商（Claude → GPT → 本地模型），只改 Agent 层，Tools 层和 CLI 层不动
- **渐进式开发**：Phase 1 先搭 Tools + CLI，Phase 2 再接 Agent，Phase 3 加 RAG。每个阶段结束时项目都能跑

### 2. 共享状态模式（Shared State Pattern）

所有 Agent 通过一个 `PaperState` 数据类传递数据：

```python
@dataclass
class PaperState:
    # 输入
    pdf_path: Path
    # Parser Agent 写入
    metadata: PaperMetadata
    full_text: str
    figure_paths: list[Path]
    references: list[str]
    # Analyst Agent 写入
    summary: str
    abstract_zh: str
    framework: str
    ...
```

每个 Agent 从 state 读取上一步的输出，处理后写回 state，下一个 Agent 接着用。这是 LangGraph 的核心设计模式——状态机（State Machine）。

**为什么不用消息传递（Message Passing）？**

- 论文分析是一个线性流水线（解析 → 分析 → 渲染），不是多轮对话
- 共享状态比消息传递更直观，调试时直接打印 state 就能看到每一步的中间结果
- LangGraph 原生支持这种模式，不需要额外封装

### 3. 降级策略（Graceful Degradation）

每个功能都有兜底方案，确保即使部分组件不可用，系统仍然能产出结果：

| 场景 | 主方案 | 兜底方案 |
|------|--------|----------|
| PDF 元数据提取 | 读取 PDF 内嵌 metadata | 启发式方法（最大字号 = 标题） |
| 图表提取 | 提取 PDF 内嵌图片对象 | 整页渲染为 PNG |
| LLM 分析 | 调用 Claude/GPT 生成分析 | 填充占位文本，仅输出元数据 |
| 摘要提取 | 正则匹配 Abstract 段落 | 返回空字符串，不崩溃 |

**为什么这样做？**

- Phase 1 没有 LLM，但管道已经能跑通
- 用户没配 API Key 时，至少能拿到 PDF 解析结果
- 面试时可以说："我的系统在任何环节失败时都不会整体崩溃"

### 4. 本地优先（Local First）

- 所有数据（论文、笔记、图片、向量库）都存在用户本地
- 不上传任何文件到云端（只有 LLM API用会发送文本）
- 向量数据库用 ChromaDB，零配置，数据存在本地文件

**为什么？**

- 科研论文可能涉及未发表的数据，保密性很重要
- 不依赖外部服务，离线也能用（除了 LLM 调用）
- 部署简单，`pip install` 就能用

### 5. 模板驱动（Template Driven）

笔记输出不是硬编码的格式，而是通过 Jinja2 模板渲染：

```
src/paperpilot/templates/
├── paper_note.md.j2      # 论文笔记模板
└── comparison.md.j2      # 对比表格模板
```

用户可以自定义模板，不同学科的研究者可以定义自己的笔记结构。比如化学方向可能需要"反应条件"字段，计算机方向可能需要"数据集"字段。

---

## 二、技术选型与理由

| 组件 | 选择 | 为什么选它 | 备选方案及放弃原因 |
|------|------|-----------|-------------------|
| Agent 框架 | **LangGraph** | 状态机模式适合多步骤工作流；比 CrewAI 更灵活，可以精确控制每一步；社区活跃，LangChain 生态 | CrewAI（太黑盒，难以调试）、纯 API 调用（缺少编排能力） |
| LLM | **Claude API** + OpenAI 兼容 | Claude 200K 上下文窗口适合长论文；同时支持 OpenAI 接口方便用户切换 | 仅 OpenAI（上下文窗口较短）、本地模型（质量不够） |
| PDF 解析 | **PyMuPDF (fitz)** | 速度快，支持文本+图片+元数据提取，C 底层性能好 | pdfplumber（慢）、marker（重，依赖多） |
| 向量存储 | **ChromaDB** | 轻量、本地运行、零配置、Python 原生 | FAISS（需要手动管理索引）、Pinecone（云服务，不符合本地优先） |
| CLI 框架 | **Typer + Rich** | 类型注解驱动，自动生成帮助文档；Rich 让终端输出美观 | argparse（太啰嗦）、click（Typer 底层就是 click，但 Typer 更简洁） |
| 模板引擎 | **Jinja2** | Python 生态最成熟的模板引擎，Flask/Django 都用它 | 字符串 format（不够灵活）、Mako（社区小） |
| 包管理 | **uv + pyproject.toml** | 比 pip 快 100 倍（Rust 实现），一个工具管理 Python 版本+虚拟环境+依赖 | pip + venv（慢，需要多个工具配合）、poetry（慢，锁文件冲突多） |
| 测试 | **pytest** | Python 社区标准，简洁，插件丰富 | unittest（太啰嗦） |

---

## 三、项目结构详解

```
paperpilot/
├── pyproject.toml              # 项目配置（依赖、版本、CLI 入口）
├── src/
│   └── paperpilot/
│       ├── __init__.py
│       ├── config.py           # 配置管理（API Key、模型、输出目录）
│       ├── cli.py              # CLI 入口（read / compare / search 三个命令）
│       ├── orchestrator.py     # 工作流编排（LangGraph 状态机）
│       ├── agents/             # 智能体层
│       │   ├── parser.py       # 解析 Agent：PDF → 结构化数据
│       │   ├── analyst.py      # 分析 Agent：结构化数据 → 论文笔记
│       │   ├── compare.py      # 对比 Agent：多篇论文 → 对比表格
│       │   └── search.py       # 检索 Agent：关键词 → 相关论文
│       ├── tools/              # 工具层（纯函数，不依赖 LLM）
│       │   ├── pdf_tools.py    # PDF 文本/元数据/图片/参考文献提取
│       │   ├── figure_tools.py # 图表管理（重命名、markdown 嵌入）
│       │   ├── template_tools.py # Jinja2 模板渲染
│       │   ├── search_tools.py # 学术搜索 API（Semantic Scholar / CrossRef）
│       │   └── rag_tools.py    # 向量检索（ChromaDB）
│       ├── templates/          # Jinja2 笔记模板
│       │   ├── paper_note.md.j2
│       │   └── comparison.md.j2
│       └── store/              # 向量数据库封装
│           └── vector_store.py
├── tests/                      # 单元测试
│   ├── test_pdf_tools.py
│   └── test_template_tools.py
└── examples/                   # 使用示例和输出样本
    └── output/
```

**为什么用 src layout（`src/paperpilot/`）而不是 flat layout（`paperpilot/`）？**

flat layout 下，项目根目录的 `paperpilot/` 会被 Python 直接当作包导入，即使你没有安装它。这会导致一个隐蔽的问题：你在开发时 `import paperpilot` 导入的是本地目录，但用户 `pip install` 后导入的是安装到 site-packages 的版本。如果两者有差异（比如你忘了打包某个文件），你的测试通过了但用户那边报错。

src layout 强制你必须先 `pip install -e .`（或 `uv sync`）才能导入，开发环境和用户环境完全一致。

---

## 四、搭建步骤

### Phase 1：基础工具层（当前已完成）

**目标**：搭建项目骨架，实现 PDF 解析工具，跑通从 PDF 到笔记的完整管道（不含 LLM）。

| 步骤 | 做了什么 | 关键命令/文件 |
|------|---------|-------------|
| 1 | 安装 uv 包管理器 | `pip install uv` |
| 2 | 初始化项目 | `uv init paperpilot --lib` |
| 3 | 配置 pyproject.toml | 添加依赖、CLI 入口、项目元数据 |
| 4 | 创建目录结构 | agents/ tools/ templates/ store/ tests/ |
| 5 | 写 config.py | 单例配置，API Key 从环境变量读取 |
| 6 | 写 pdf_tools.py | 4 个核心函数：元数据/文本/图片/参考文献提取 |
| 7 | 写 figure_tools.py | 图表重命名、markdown 嵌入语法生成 |
| 8 | 写 template_tools.py | Jinja2 模板加载和渲染 |
| 9 | 写笔记模板 | paper_note.md.j2（8 个结构化部分） |
| 10 | 写 cli.py | Typer CLI，三个子命令：read / compare / search |
| 11 | 写 orchestrator.py | 工作流骨架 + PaperState 共享状态 |
| 12 | 写单元测试 | 14 个 pytest 用例，用真实论文 PDF 测试 |
| 13 | 安装依赖并测试 | `uv sync` + `uv run pytest` → 14/14 通过 |

### Phase 2：单篇分析 Agent（下一步）

**目标**：接入 LLM，实现 Parser Agent 和 Analyst Agent，让 `paperpilot read paper.pdf` 生成完整的论文笔记。

- 用 LangGraph 定义状态机工作流
- Analyst Agent 调用 Claude API，传入论文全文，按模板结构生成分析
- 风格要求：通俗易懂地讲解，遇到关键术语用括号给出简明解释

### Phase 3：多篇对比 + 检索

**目标**：实现 Compare Agent 和 Search Agent。

- ChromaDB 向量存储：已读论文自动入库
- Compare Agent：多篇论文生成对比表格
- Search Agent：通过 Semantic Scholar API 搜索相关论文
- RAG：基于已读论文库的语义问答

### Phase 4：打磨发布

**目标**：让项目在 GitHub 上有吸引力。

- 中英双语 README + demo GIF
- examples/ 目录放真实论文的分析输出
- GitHub Actions CI
- 发布到 PyPI（`pip install paperpilot`）

---

## 五、Agent 设计详解

### Agent 与 Tool 的关系

在 AI Agent 架构中，Agent 和 Tool 是两个不同的概念：

- **Tool（工具）**：一个确定性的函数，输入什么就输出什么，不涉及 LLM。比如 `extract_text(pdf)` 永远返回 PDF 的文本内容。
- **Agent（智能体）**：一个由 LLM 驱动的决策单元，它可以调用 Tool，也可以根据上下文决定下一步做什么。比如 Analyst Agent 读取论文文本后，决定哪些是关键结果、哪些是创新点。

```
Agent = LLM（决策能力） + Tools（执行能力） + Prompt（任务指令）
```

### 四个 Agent 的分工

| Agent | 输入 | 输出 | 是否需要 LLM | 可调用的 Tools |
|-------|------|------|-------------|---------------|
| Parser | PDF 文件 | 结构化数据（文本、元数据、图片、参考文献） | 否 | pdf_tools, figure_tools |
| Analyst | 结构化数据 | 论文笔记（8 个部分） | 是 | template_tools, glossary_lookup |
| Compare | 多篇论文的分析结果 | 对比表格 + 综合分析 | 是 | template_tools, rag_tools |
| Search | 搜索关键词 | 相关论文列表 | 否 | search_tools (Semantic Scholar API) |

注意 Parser Agent 和 Search Agent 不需要 LLM——它们的工作是确定性的（解析 PDF、调用搜索 API）。只有 Analyst 和 Compare 需要 LLM 来做理解和分析。

这种设计减少了 LLM 调用次数（省钱），也让不需要 LLM 的部分更快、更可靠。

### 工作流编排

```
paperpilot read paper.pdf
        │
        ▼
   ┌─────────┐     确定性处理，不调用 LLM
   │ Parser  │──→  提取文本、元数据、图片、参考文献
   │ Agent   │     写入 PaperState
   └────┬────┘
        │
        ▼
   ┌─────────┐     调用 Claude API
   │ Analyst │──→  生成一段话总结、摘要翻译、框架、
   │ Agent   │     研究问题、方法、结果、创新点、局限性
   └────┬────┘     写入 PaperState
        │
        ▼
   ┌─────────┐     确定性处理，不调用 LLM
   │ Render  │──→  用 Jinja2 模板 + PaperState 数据
   │         │     渲染生成 markdown 笔记文件
   └─────────┘
```

---

## 六、关键设计决策记录

### 决策 1：为什么选 LangGraph 而不是直接调 API？

直接调 Claude API 也能实现同样的功能，但 LangGraph 提供了：

- **状态管理**：自动追踪每一步的输入输出，方便调试
- **可视化**：LangGraph 可以导出工作流图，放在 README 里很直观
- **可扩展**：后续加新 Agent（比如翻译 Agent）只需要加一个节点
- **面试价值**：展示你理解 Agent 编排框架，而不只是会调 API

### 决策 2：为什么 Parser Agent 不用 LLM？

PDF 解析是确定性任务——同一个 PDF 每次解析结果应该一样。用 LLM 做这件事既慢又贵，还可能出错（幻觉）。把确定性工作和需要推理的工作分开，是 Agent 系统设计的基本原则。

### 决策 3：为什么笔记模板要求"通俗易懂 + 术语解释"？

科研论文的原文通常很晦涩。如果 Agent 只是摘抄原文，那和直接读论文没区别。通俗讲解 + 术语即时解释的风格，让笔记真正成为"读过就懂"的参考资料，这是产品层面的差异化。

### 决策 4：为什么用 src layout？

防止开发环境和安装环境的导入路径不一致。详见第三节"项目结构详解"。

### 决策 5：为什么先写 Tools 再写 Agent？

自底向上（Bottom-Up）的开发顺序：

1. 先写 Tools → 可以独立测试，确保 PDF 解析正确
2. 再写 Agent → Agent 调用已经验证过的 Tools，减少 bug 来源
3. 最后写 Orchestrator → 把已经能工作的 Agent 串起来

如果自顶向下（先写 Orchestrator），每一层都依赖下一层的假实现，调试时不知道 bug 出在哪一层。

---

## 七、面试话术参考

> **Q：这个项目的架构是怎么设计的？**
>
> A：四层架构——Tools 层做确定性的 PDF 解析和文件操作，Agent 层用 LLM 做理解和分析，Orchestrator 层用 LangGraph 状态机编排多个 Agent 的执行顺序，CLI 层处理用户交互。每层只依赖下一层，可以独立测试和替换。

> **Q：为什么用 LangGraph？**
>
> A：论文分析是一个多步骤的工作流——先解析 PDF，再用 LLM 分析，最后渲染输出。LangGraph 的状态机模式天然适合这种场景。相比 CrewAI 这种黑盒框架，LangGraph 让我能精确控制每一步的输入输出和错误处理。

> **Q：Agent 和 Tool 有什么区别？**
>
> A：Tool 是确定性的函数，比如从 PDF 提取文本，输入一样输出就一样。Agent 是 LLM 驱动的决策单元，它根据上下文决定怎么理解和分析内容。我的设计原则是：能用 Tool 解决的不用 Agent，减少 LLM 调用，既省钱又更可靠。

> **Q：你怎么保证代码质量？**
>
> A：三个层面。第一，用真实论文 PDF 做集成测试，不是 mock 数据。第二，分层架构让每一层可以独立测试。第三，降级策略确保任何环节失败时系统不会整体崩溃。
