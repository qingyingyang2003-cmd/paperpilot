# Phase 2：Analyst Agent — 接入 LLM，让论文"读得懂"

## 这一步做了什么

Phase 1 搭好了管道：PDF 进去 → 提取文本/图片/元数据 → 用模板渲染出笔记。但笔记里全是占位符"（待 LLM 分析）"，因为还没有接入大语言模型。

Phase 2 做的事情就是：**把 LLM 接进来，让 Analyst Agent 真正"读"论文，输出结构化的分析结果。**

具体新增/修改了三个文件：

| 文件 | 作用 |
|------|------|
| `src/paperpilot/agents/analyst.py` | 核心：调用 Claude/GPT 分析论文，返回 8 个结构化字段 |
| `src/paperpilot/orchestrator.py` | 更新 `_run_analyst()` 的错误处理和降级逻辑 |
| `tests/test_analyst.py` | 25 个单元测试，覆盖 prompt 构建、响应解析、边界情况 |

改完之后，`paperpilot read paper.pdf` 的完整流程就打通了：

```
PDF → Parser Agent（提取文本）→ Analyst Agent（LLM 分析）→ 模板渲染 → 输出笔记
```

---

## 为什么要这么做：设计决策逐条解释

### 决策 1：用 XML 标签做结构化输出

Analyst Agent 需要让 LLM 返回 8 个字段（summary、methods、results……）。怎么从一大段文本里拆出这些字段？有三种常见方案：

| 方案 | 优点 | 缺点 |
|------|------|------|
| 让 LLM 返回 JSON | 结构严格，程序好解析 | 长文本容易出现 JSON 格式错误（漏逗号、引号未转义），而且 JSON 里写大段中文可读性很差 |
| LangChain `with_structured_output()` | 框架原生支持，用 Pydantic 定义 schema | 底层走 tool calling 协议，会限制模型的生成自由度，分析质量可能下降 |
| **XML 标签包裹** | Claude 对 XML 理解极好（训练数据中大量 XML），文本自然流畅，解析只需简单正则 | 需要自己写解析函数（但很简单） |

**选择了 XML 方案。** 核心原因：论文分析是长文本生成任务，模型需要自由发挥，不能被 JSON 的格式约束卡住。XML 标签只是"分隔符"，标签内部的文本完全自由。

代码实现：

```python
# 发给 LLM 的 prompt 里要求用 XML 标签包裹每个部分
"""
<summary>
A concise paragraph summarizing the paper...
</summary>

<methods>
Describe the methodology in detail...
</methods>
"""

# 解析时用正则提取
def _extract_tag(content: str, tag: str) -> str:
    pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""
```

`re.DOTALL` 让 `.` 匹配换行符，这样标签内可以有多行文本。`.*?` 是非贪婪匹配，防止跨标签匹配。

**面试怎么说**：我对比了 JSON、Pydantic structured output、XML 三种方案，选择 XML 是因为 Claude 对 XML 的理解能力很强，而且长文本生成场景下 JSON 容易出格式错误。解析只需要一行正则。

---

### 决策 2：Prompt 的三段式结构

发给 LLM 的 prompt 分三部分：

```
┌─────────────────────────────────┐
│  1. System Instruction          │  ← 角色定义 + 语言要求 + 输出格式
│     "你是论文分析助手，用中文输出，  │
│      术语保留英文并标注翻译..."     │
├─────────────────────────────────┤
│  2. Paper Metadata              │  ← 标题、作者、期刊、年份、DOI
│     <paper_metadata>            │     给 LLM 上下文，帮助它理解论文背景
│     Title: ...                  │
│     </paper_metadata>           │
├─────────────────────────────────┤
│  3. Paper Full Text             │  ← 论文全文（可能截断）
│     <paper_text>                │
│     Introduction: ...           │
│     </paper_text>               │
└─────────────────────────────────┘
```

**为什么要单独传 metadata？**

论文全文是从 PDF 提取的纯文本，格式混乱（页眉页脚混在一起、公式变成乱码）。单独传一份干净的 metadata，让 LLM 至少能准确知道标题、作者、期刊这些基本信息，不会因为 PDF 解析质量差而搞错。

**为什么语言指令要这么具体？**

不能只说"用中文"。必须明确：
- 专业术语保留英文（SICM 不翻译成"扫描离子电导显微镜"，而是写 "SICM（扫描离子电导显微镜）"）
- 首次出现时标注翻译，后续直接用英文缩写
- 风格要"通俗易懂，像在给同领域的研究生讲解"

这些细节直接决定了输出质量。模糊的指令 → 模糊的输出。

---

### 决策 3：文本截断策略 — 80/20 分割

论文全文可能很长（一篇 20 页的论文约 5 万字符），超过 LLM 的上下文窗口。需要截断，但怎么截？

```python
def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    
    head_size = int(max_chars * 0.8)  # 前 80%
    tail_size = max_chars - head_size  # 后 20%
    
    head = text[:head_size]
    tail = text[-tail_size:]
    
    return f"{head}\n\n[... truncated ...]\n\n{tail}"
```

**为什么是 80/20 而不是 50/50？**

论文的结构通常是：

```
Introduction（背景、问题定义）     ← 最重要，理解论文的基础
Methods（实验方法、技术细节）       ← 很重要，分析的核心
Results（详细数据、图表描述）       ← 中间部分，往往最长但信息密度低
Discussion（讨论、与前人对比）      ← 重要
Conclusion（总结、未来工作）        ← 重要，通常在最后
```

前 80% 覆盖了 Introduction + Methods + 大部分 Results，后 20% 覆盖了 Conclusion。被截掉的中间部分通常是重复的数据描述（"Figure 3a shows..."、"Table 2 summarizes..."），LLM 可以从上下文推断。

**面试怎么说**：我没有简单地截断前 N 个字符，而是保留了论文的头部（引言+方法）和尾部（结论），因为这两部分信息密度最高。中间的详细数据描述被截掉后，LLM 仍然能从上下文推断出关键结果。

---

### 决策 4：多 Provider 支持 — 工厂模式

```python
def _create_llm():
    provider = config.llm.provider  # "anthropic" 或 "openai"
    
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=config.llm.model, ...)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=config.llm.model, ...)
```

这是一个简单的**工厂模式（Factory Pattern）**：根据配置创建不同的 LLM 客户端，但返回统一的接口（LangChain 的 `BaseChatModel`）。调用方不需要知道底层用的是 Claude 还是 GPT。

**为什么用延迟导入（`from ... import` 放在函数内部）？**

```python
# 不是在文件顶部 import，而是在函数内部
def _create_llm():
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # ← 延迟导入
```

两个原因：
1. **启动速度**：`langchain_anthropic` 和 `langchain_openai` 都是重量级包，导入需要几百毫秒。如果放在文件顶部，用户只是跑 `paperpilot --help` 也要等这些包加载完。延迟导入让"不需要 LLM 的操作"保持快速。
2. **可选依赖**：用户如果只用 Anthropic，不需要安装 `langchain-openai`。延迟导入让缺少某个包时不会在 import 阶段就崩溃。

**面试怎么说**：我用工厂模式封装了 LLM 的创建，通过配置切换 Anthropic/OpenAI。延迟导入避免了重量级依赖拖慢 CLI 启动速度——用户跑 `--help` 不需要等 LangChain 加载。

---

### 决策 5：三层降级策略（Graceful Degradation）

`_run_analyst()` 的错误处理不是简单的 try/except，而是区分了不同的失败场景：

```python
def _run_analyst(state):
    try:
        from paperpilot.agents.analyst import analyze_paper
        state = analyze_paper(state)          # 正常路径
    except RuntimeError as e:
        # 场景 1：没配 API Key → 明确告诉用户怎么配
        state = _fill_placeholder(state)
    except Exception as e:
        # 场景 2：网络错误、API 限流、解析失败 → 降级到 metadata-only
        state = _fill_placeholder(state)
```

三种结果：

| 场景 | 发生条件 | 用户看到的 |
|------|---------|-----------|
| 成功 | API Key 配好，网络正常 | 完整的 8 段分析笔记 |
| 降级 A | 没配 API Key | 笔记只有元数据 + 提示"请配置 API Key" |
| 降级 B | 网络超时 / API 报错 | 笔记只有元数据 + 错误信息 |

**关键原则：永远不崩溃，永远给用户一个结果。**

Phase 1 的时候 Analyst Agent 还没实现，但管道已经能跑通（输出占位符笔记）。Phase 2 接入 LLM 后，即使 LLM 不可用，管道仍然能跑通。这就是降级策略的价值——系统的可用性不依赖于任何单一组件。

**面试怎么说**：我的系统在任何环节失败时都不会整体崩溃。没有 API Key 时输出 metadata-only 笔记，API 报错时降级到已有数据。这是生产级系统的基本要求——graceful degradation。

---

### 决策 6：参数字段的特殊处理

8 个分析字段中，`parameters` 和 `key_references` 需要特殊处理：

```python
# 其他字段：直接存字符串
state.summary = "本文首次使用 SICM..."

# parameters：解析成 dict（模板里要遍历 key-value）
state.parameters = {
    "Probe aperture": "~220 nm",
    "Electrolyte": "50 mM KCl",
    "Scan mode": "Hopping mode",
}

# key_references：解析成 list（模板里要遍历列表）
state.key_references = [
    "Perry et al., JACS 2016 — SICM 方法论文",
    "Kang et al., ACS Nano 2017 — hopping mode",
]
```

**为什么不全用字符串？**

因为 Jinja2 模板需要遍历它们：

```jinja2
{# 参数表格需要 key-value 遍历 #}
{% for key, value in parameters.items() %}
- {{ key }}：{{ value }}
{% endfor %}

{# 参考文献需要列表遍历 #}
{% for ref in references %}
- {{ ref }}
{% endfor %}
```

如果 parameters 是一个大字符串，模板就没法生成整齐的列表。数据结构要匹配模板的渲染需求。

---

## 测试策略：不花钱也能测

Analyst Agent 的核心逻辑是调用 LLM API，但测试不能每次都花钱调真实 API。解决方案：**把"调 API"和"处理结果"拆开测试。**

```
analyze_paper()
    │
    ├── _build_prompt()      ← 可以独立测试：输入 state，检查 prompt 内容
    │
    ├── llm.invoke(prompt)   ← 这一步调真实 API，测试时跳过
    │
    └── _parse_response()    ← 可以独立测试：输入模拟的 XML，检查解析结果
```

25 个测试分五组：

| 测试组 | 测什么 | 示例 |
|--------|--------|------|
| TestBuildPrompt (5) | prompt 包含论文文本、metadata、正确的语言指令 | `assert "中文" in prompt` |
| TestExtractTag (4) | XML 标签提取：基本、多行、缺失、空白处理 | `_extract_tag("<summary>Hello</summary>", "summary") == "Hello"` |
| TestParseResponse (5) | 完整响应解析、部分响应、空响应 | 模拟 LLM 返回的 XML → 检查 state 的 8 个字段 |
| TestParseParameters (4) | "key: value" 格式解析、bullet 前缀、N/A、空输入 | `"Aperture: 220 nm"` → `{"Aperture": "220 nm"}` |
| TestParseReferences (4) | bullet 列表、编号列表、短行过滤、空输入 | `"- Perry et al., JACS 2016"` → `["Perry et al., JACS 2016"]` |
| TestTruncateText (3) | 短文本不变、长文本截断、保留头尾 | 验证 "INTRO_" 和 "_CONCLUSION" 都在截断结果中 |

**面试怎么说**：我把 LLM 调用和数据处理拆开了。prompt 构建和响应解析都是纯函数，可以用确定性的输入输出测试，不需要调真实 API。这样 CI 可以免费跑，测试也是确定性的（不会因为 LLM 输出波动而 flaky）。

---

## 数据流全景图

```
paperpilot read paper.pdf --lang zh
        │
        ▼
┌──────────────────────────────────────────────────┐
│  CLI Layer (cli.py)                              │
│  解析命令行参数 → 调用 run_read_workflow()         │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│  Orchestrator (orchestrator.py)                  │
│                                                  │
│  PaperState = { pdf_path, language: "zh" }       │
│       │                                          │
│       ▼                                          │
│  _run_parser(state)                              │
│       │  调用 pdf_tools 提取文本/图片/元数据        │
│       │  state.full_text = "Introduction: ..."   │
│       │  state.metadata = { title, authors, ... } │
│       ▼                                          │
│  _run_analyst(state)                             │
│       │  调用 analyst.py                          │
│       │    1. _create_llm() → ChatAnthropic      │
│       │    2. _build_prompt(state) → 三段式 prompt │
│       │    3. llm.invoke(prompt) → XML 响应       │
│       │    4. _parse_response() → 填充 state      │
│       │  state.summary = "本文首次使用 SICM..."    │
│       │  state.methods = "hopping mode + ..."     │
│       ▼                                          │
│  _render_and_save(state)                         │
│       │  Jinja2 模板 + state 数据 → markdown 文件  │
│       ▼                                          │
│  返回 { note_path, figures }                      │
└──────────────────────────────────────────────────┘
```

---

## 涉及的设计模式总结

| 模式 | 在哪里用的 | 解决什么问题 |
|------|-----------|-------------|
| **工厂模式** (Factory) | `_create_llm()` | 根据配置创建不同的 LLM 客户端，调用方不关心具体实现 |
| **共享状态** (Shared State) | `PaperState` dataclass | 多个 Agent 之间传递数据，每个 Agent 读取上一步的输出、写入自己的结果 |
| **策略模式** (Strategy) | LangChain 的 `BaseChatModel` | Anthropic 和 OpenAI 实现同一个接口，可以互换 |
| **优雅降级** (Graceful Degradation) | `_run_analyst()` 的 try/except | 任何环节失败都不崩溃，给用户一个可用的结果 |
| **延迟导入** (Lazy Import) | `_create_llm()` 内部的 import | 避免重量级依赖拖慢 CLI 启动速度 |
| **关注点分离** (Separation of Concerns) | prompt 构建 / API 调用 / 响应解析 三个独立函数 | 每个函数只做一件事，可以独立测试 |

---

## 与 Phase 1 的关系

Phase 1 搭好了"水管"（PDF → 提取 → 模板 → 笔记），Phase 2 接上了"水源"（LLM）。

关键的是：Phase 1 结束时管道已经能跑通（输出占位符），Phase 2 只是把占位符替换成了真实的 LLM 分析结果。这种**渐进式开发**的好处是：

1. 每个 Phase 结束时项目都是可运行的，不存在"半成品"
2. 如果 Phase 2 的 LLM 接入出了问题，Phase 1 的功能不受影响
3. 面试时可以说："我的项目从第一天就能跑，每个阶段都在已验证的基础上增量开发"

这也是为什么 orchestrator.py 里的 `_run_analyst()` 从一开始就有 try/except 和 placeholder 逻辑——它是为 Phase 2 预留的接口，Phase 1 时用 placeholder 填充，Phase 2 时替换成真实实现。**接口先行，实现后补。**
