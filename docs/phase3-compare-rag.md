# Phase 3：Compare Agent + Search Agent + RAG — 架构解释文档

## 这一步做了什么

Phase 2 实现了单篇论文分析（`paperpilot read`）。Phase 3 补齐了两个核心能力：

1. **多篇论文对比**（`paperpilot compare a.pdf b.pdf c.pdf`）— 用 LLM 生成对比表格 + 综合分析
2. **语义搜索**（`paperpilot search "SICM"`）— Semantic Scholar 外部搜索 + ChromaDB 本地已读论文匹配

新增/修改了 6 个文件：

| 文件 | 作用 |
|------|------|
| `src/paperpilot/agents/compare.py` | Compare Agent：多篇论文 → LLM 对比分析 |
| `src/paperpilot/store/vector_store.py` | ChromaDB 向量库封装：入库、语义搜索、列表、删除 |
| `src/paperpilot/orchestrator.py` | 实现 `run_compare_workflow()` + `run_search_workflow()` + 自动入库 |
| `src/paperpilot/cli.py` | search 命令分"外部搜索"和"本地匹配"两部分展示 |
| `tests/test_compare.py` | 20 个测试：prompt 构建 + 响应解析 + fallback |
| `tests/test_vector_store.py` | 16 个测试：入库 + 搜索 + 去重 + 删除 |

测试结果：**83 passed, 4 skipped**（skipped 的是需要网络的集成测试）。

---

## 为什么要这么做：设计决策逐条解释

### 决策 1：为什么用 ChromaDB 做向量库？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **ChromaDB** | 零配置、本地运行、Python 原生、自带 embedding 模型 | 不适合超大规模（百万级） |
| FAISS | 速度极快、Meta 出品 | 需要手动管理索引文件、不自带 embedding |
| Pinecone | 云托管、自动扩展 | 需要注册账号、数据上传到云端（违反 local-first 原则） |
| SQLite + FTS5 | 轻量、无依赖 | 只支持关键词搜索，不支持语义搜索 |

**选择 ChromaDB** 的核心原因：

1. **零配置**：`pip install chromadb` 就能用，不需要启动服务、不需要 API key
2. **自带 embedding**：内置 all-MiniLM-L6-v2 模型，本地运行，不需要调用外部 API
3. **持久化**：数据自动存到本地目录（`.paperpilot/chroma/`），重启后数据还在
4. **规模匹配**：科研场景下一个人读的论文通常在几十到几百篇，ChromaDB 完全够用

```python
class PaperVectorStore:
    def __init__(self, persist_dir=".paperpilot/chroma"):
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection("paperpilot_papers")
```

**面试怎么说**：我选 ChromaDB 是因为它符合项目的 local-first 原则——数据不出本地，零配置，自带 embedding 模型。对于科研场景（几十到几百篇论文），它的性能完全够用。如果未来需要扩展到万级论文，可以换成 FAISS 或 Qdrant，接口层已经抽象好了。

---

### 决策 2：向量化什么内容？

一篇论文有很多字段（标题、摘要、全文、方法、结果……），不能全部塞进向量。需要选择**信息密度最高**的字段组合：

```python
def add_paper(self, state: PaperState) -> None:
    parts = [
        f"Title: {state.metadata.title}",
        f"Abstract: {state.metadata.abstract}",
        f"Summary: {state.summary}",
        f"Research Question: {state.research_question}",
        f"Methods: {state.methods}",
    ]
    document = "\n\n".join(parts)
```

**为什么选这 5 个字段？**

- **Title**：最浓缩的语义信息，搜索时权重最高
- **Abstract**：作者自己写的摘要，覆盖了论文的核心贡献
- **Summary**：Analyst Agent 生成的一段话总结，比 abstract 更通俗
- **Research Question**：明确了论文解决什么问题，搜索"如何做 X"时命中率高
- **Methods**：技术方法关键词，搜索"SICM hopping mode"时能匹配

**为什么不用全文？**

全文太长（几万字符），embedding 模型有 token 限制（all-MiniLM-L6-v2 最大 256 tokens）。超出部分会被截断，反而稀释了关键信息。选择信息密度高的字段组合，效果比塞全文更好。

**面试怎么说**：我选择了 title + abstract + summary + research_question + methods 五个字段做 embedding，因为它们信息密度最高。全文太长会被 embedding 模型截断，反而降低检索质量。这是 RAG 系统设计中"chunking strategy"的一个变体——我用的是"field-level chunking"而不是"fixed-size chunking"。

---

### 决策 3：自动入库的时机和容错

```python
# orchestrator.py — run_read_workflow() 末尾
def _index_paper(state: PaperState) -> None:
    try:
        from paperpilot.store.vector_store import PaperVectorStore
        store = PaperVectorStore()
        store.add_paper(state)
    except Exception:
        pass  # 入库失败不影响主流程
```

**为什么在 read workflow 末尾自动入库？**

用户不需要手动执行"入库"操作。每次 `paperpilot read paper.pdf` 成功后，论文自动进入向量库。下次搜索时就能找到它。这是**零摩擦设计**——用户甚至不需要知道向量库的存在。

**为什么用 try/except 包裹？**

入库是"锦上添花"功能，不是核心流程。如果 ChromaDB 出了问题（磁盘满了、权限问题、依赖缺失），笔记已经生成好了，不应该因为入库失败而报错。这是 graceful degradation 原则的又一个应用。

**为什么用 `upsert` 而不是 `add`？**

```python
self._collection.upsert(ids=[doc_id], documents=[document], metadatas=[metadata])
```

用户可能对同一篇论文跑多次 `paperpilot read`（比如换了模板或语言）。`upsert` 保证同一个 DOI 只有一条记录，避免重复。

---

### 决策 4：Compare Agent 的 Prompt 设计

对比 N 篇论文时，prompt 需要把每篇论文的关键信息都传给 LLM。挑战是：

- 每篇论文的 methods/results 可能很长（几百字）
- N 篇论文加起来可能超过上下文窗口
- LLM 需要同时"看到"所有论文才能做有意义的对比

**解决方案：传关键字段，不传全文**

```python
def _build_compare_prompt(states, language):
    for i, state in enumerate(states, 1):
        block = f"""<paper_input index="{i}">
Title: {state.metadata.title}
Research Question: {state.research_question}
Methods: {state.methods}
Results: {state.results}
Innovations: {state.innovations}
Limitations: {state.limitations}
</paper_input>"""
```

每篇论文只传 6 个字段（已经是 Analyst Agent 分析过的精华），不传全文。这样 5 篇论文加起来也不会超过上下文窗口。

**输出要求：简要版本 + 综合分析**

LLM 需要做两件事：
1. 为每篇论文生成**简要版本**（每个字段 1-2 句话，适合放进表格单元格）
2. 写一段**综合分析**（对比异同、研究趋势、建议方向）

这两个任务的性质不同：简要版本是"压缩"，综合分析是"推理"。放在同一个 prompt 里让 LLM 一次完成，比分两次调用更高效（省钱 + 上下文一致）。

---

### 决策 5：Search Workflow 的双源合并

```python
def run_search_workflow(query, limit):
    results = []
    
    # Source 1: Semantic Scholar（外部，200M+ 论文）
    papers = SemanticScholarSource().search(query, limit)
    results.extend(...)
    
    # Source 2: Local ChromaDB（本地，已读论文）
    local_results = PaperVectorStore().search(query, n_results=5)
    # 按 DOI 去重
    existing_dois = {r["doi"] for r in results}
    for paper in local_results:
        if paper["doi"] not in existing_dois:
            results.append(paper)
    
    return results
```

**为什么要两个源？**

- **Semantic Scholar**：覆盖面广（2 亿+论文），但结果是"冷"的——你没读过这些论文
- **本地向量库**：覆盖面窄（只有你读过的），但结果是"热"的——你已经有笔记了

两者互补：外部搜索帮你发现新论文，本地搜索帮你回忆已读论文。

**为什么按 DOI 去重？**

同一篇论文可能同时出现在 Semantic Scholar 结果和本地库中。去重避免用户看到重复条目。DOI 是论文的唯一标识符，用它做去重键最可靠。

**CLI 分两部分展示**：

```
Semantic Scholar (8 results)
  1. Paper A...
  2. Paper B...

Local Library (2 matches)
  1. Paper C... (Note: notes/paper-c.md)
```

本地匹配额外显示笔记路径，方便用户直接打开已有笔记。

---

### 决策 6：Compare Agent 的 Fallback 策略

和 Analyst Agent 一样，Compare Agent 也有降级方案：

```python
try:
    comparison = compare_papers(states, language)
except RuntimeError:
    # 没有 API Key
    comparison = compare_papers_fallback(states)
except Exception:
    # API 错误
    comparison = compare_papers_fallback(states)
```

`compare_papers_fallback()` 不调用 LLM，直接用 metadata 生成对比表格：
- `short_title` = 第一作者姓 + 年份（如 "Maddar 2019"）
- 长字段截断到 150 字符 + "..."
- 没有综合分析（`analysis = ""`）

用户至少能看到一个基本的对比表格，而不是一个报错。

---

## 数据流全景图

### Compare 流程

```
paperpilot compare a.pdf b.pdf c.pdf
        │
        ▼
┌──────────────────────────────────────────────────┐
│  对每篇 PDF 分别执行：                             │
│    _run_parser() → _run_analyst()                │
│  得到 list[PaperState]（每篇都有完整分析）          │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│  Compare Agent                                   │
│    _build_compare_prompt(states)                 │
│    → 把每篇论文的 6 个关键字段打包                  │
│    llm.invoke(prompt)                            │
│    → LLM 生成简要版本 + 综合分析                   │
│    _parse_compare_response(content)              │
│    → 解析 XML 为 dict                            │
└──────────────────┬───────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────┐
│  Jinja2 渲染 comparison.md.j2                    │
│    → 生成 Markdown 对比表格 + 综合分析文本          │
└──────────────────────────────────────────────────┘
```

### Search 流程

```
paperpilot search "SICM surface charge"
        │
        ├─────────────────────────────────┐
        ▼                                 ▼
┌─────────────────┐              ┌─────────────────┐
│ Semantic Scholar │              │ ChromaDB 向量库  │
│ API 搜索         │              │ 语义搜索         │
│ (外部 200M+ 论文) │              │ (本地已读论文)    │
└────────┬────────┘              └────────┬────────┘
         │                                │
         └────────────┬───────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ 按 DOI 去重    │
              │ 合并结果       │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ CLI 分两部分   │
              │ 展示结果       │
              └───────────────┘
```

### 自动入库流程

```
paperpilot read paper.pdf
        │
        ▼
   Parser → Analyst → Render Note
        │
        ▼ (新增)
   _index_paper(state)
        │
        ▼
   ChromaDB.upsert(title + abstract + summary + ...)
        │
        ▼
   下次 search 时可以找到这篇论文
```

---

## 涉及的设计模式和概念

| 概念 | 在哪里用的 | 解释 |
|------|-----------|------|
| **RAG（检索增强生成）** | search workflow | 先从向量库检索相关文档，再结合外部搜索结果。虽然这里没有"生成"步骤，但检索部分是标准 RAG 架构 |
| **Embedding（向量嵌入）** | ChromaDB 入库 | 把文本转换成高维向量（768 维），语义相近的文本在向量空间中距离近 |
| **Upsert（更新或插入）** | add_paper() | 如果 DOI 已存在则更新，否则插入。避免重复数据 |
| **去重（Deduplication）** | search workflow | 按 DOI 去重，避免同一篇论文在外部和本地结果中重复出现 |
| **Graceful Degradation** | _index_paper(), compare fallback | 入库失败不崩溃，LLM 不可用时用 metadata 降级 |
| **延迟导入** | orchestrator 中的 import | ChromaDB 是重量级依赖，只在需要时导入 |
| **Field-level Chunking** | 向量化内容选择 | 不用 fixed-size chunking，而是选择信息密度高的字段组合 |

---

## RAG 基础知识补充

RAG（Retrieval-Augmented Generation）是当前 AI 应用最常见的架构模式之一。面试中经常被问到。

### 什么是 RAG？

```
用户提问 → 检索相关文档 → 把文档 + 问题一起发给 LLM → LLM 基于文档回答
```

传统 LLM 只能用训练数据回答问题。RAG 让 LLM 能"查阅"你的私有数据（论文、笔记、代码），然后基于这些数据回答。

### PaperPilot 中的 RAG

我们的 RAG 是"轻量版"——目前只用了检索部分（从向量库找相关论文），没有把检索结果再发给 LLM 做生成。但架构已经就位，Phase 3+ 可以轻松扩展为：

```
用户: "SICM 在活细胞上的应用有哪些？"
    │
    ├─ 向量库检索 → 找到 3 篇相关已读论文
    │
    ├─ 把 3 篇论文的摘要 + 用户问题发给 LLM
    │
    └─ LLM 基于这 3 篇论文生成回答（带引用）
```

### Embedding 是怎么工作的？

```
"SICM surface charge hair" 
    → all-MiniLM-L6-v2 模型 
    → [0.12, -0.34, 0.56, ..., 0.78]  (768 维向量)

"扫描离子电导显微镜 表面电荷 头发"
    → [0.11, -0.33, 0.55, ..., 0.77]  (语义相近 → 向量相近)

"深度学习 图像分类 CNN"
    → [0.89, 0.12, -0.67, ..., -0.23]  (语义不同 → 向量远)
```

ChromaDB 用余弦距离（cosine distance）衡量两个向量的相似度。距离越小 = 语义越相近。

### 面试常见问题

> **Q：你的 RAG 系统是怎么设计的？**
>
> A：入库时，我把论文的 title + abstract + summary + research_question + methods 拼接后用 all-MiniLM-L6-v2 做 embedding，存入 ChromaDB。搜索时，用户的 query 也做 embedding，然后在向量空间中找最近邻。我选择 field-level chunking 而不是 fixed-size chunking，因为论文的结构化字段信息密度更高。

> **Q：为什么不用全文做 embedding？**
>
> A：all-MiniLM-L6-v2 的 max token 是 256。全文几万字符会被截断，只保留开头部分（通常是标题和摘要），后面的方法和结果全丢了。不如我手动选择 5 个关键字段拼接，确保每个重要维度都有覆盖。

> **Q：ChromaDB 和 FAISS 有什么区别？**
>
> A：ChromaDB 是"全包"方案——自带 embedding 模型、自动持久化、支持 metadata 过滤。FAISS 只做向量检索，embedding 和持久化需要自己实现。对于我这个项目（几百篇论文），ChromaDB 的便利性远大于 FAISS 的性能优势。

---

## 测试策略

和 Phase 2 一样，不调用真实 API：

| 测试文件 | 测什么 | 方法 |
|----------|--------|------|
| `test_compare.py` (20 tests) | prompt 构建、XML 解析、fallback | 用 fixture 模拟 LLM 响应 |
| `test_vector_store.py` (16 tests) | 入库、搜索、去重、删除 | 用 `tmp_path` 创建临时 ChromaDB |

ChromaDB 测试的关键技巧：用 pytest 的 `tmp_path` fixture 创建临时目录，测试结束后自动清理。不会污染用户的真实向量库。

```python
@pytest.fixture
def tmp_store(tmp_path: Path) -> PaperVectorStore:
    return PaperVectorStore(persist_dir=str(tmp_path / "chroma"))
```

---

## 与前几个 Phase 的关系

```
Phase 1:  Tools 层（PDF 解析、模板渲染）
              │
Phase 1.5: Sources 层（Semantic Scholar、x-mol）
              │
Phase 2:  Analyst Agent（单篇分析）
              │
Phase 3:  Compare Agent + Vector Store + Search Workflow
              │
              ├─ Compare Agent 复用了 Analyst Agent 的 LLM 工厂和 XML 解析模式
              ├─ Search Workflow 复用了 Sources 层的 SemanticScholarSource
              └─ Vector Store 在 Read Workflow 末尾自动入库（无缝集成）
```

每个 Phase 都在前一个 Phase 的基础上增量构建，复用已有代码，不重复造轮子。这就是分层架构的价值——新功能只需要在正确的层添加代码，不需要改动其他层。
