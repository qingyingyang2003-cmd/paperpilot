"""Analyst Agent — LLM-powered paper analysis.

Takes extracted text from a PDF and produces structured analysis:
summary, abstract translation, framework, research questions,
methods, results, innovations, and limitations.

Design decisions:
- Uses XML tags for structured output (Claude handles XML very well)
- Supports both Anthropic (Claude) and OpenAI (GPT) via LangChain
- Truncates input to fit context window (papers can be very long)
- Graceful degradation: returns partial results on error
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from paperpilot.config import config

if TYPE_CHECKING:
    from paperpilot.orchestrator import PaperState

# Max characters to send to LLM (roughly 100k tokens for Claude)
# Most papers are 5k-15k words; we keep a generous limit
MAX_TEXT_CHARS = 120_000


# ---------------------------------------------------------------------------
# Public API — called by orchestrator graph nodes
# ---------------------------------------------------------------------------
def analyze_paper_from_state(state: "PaperState") -> dict[str, Any]:
    """Analyze a paper using LLM, returning a partial state update dict.

    This is the main entry point called by the orchestrator's analyze_node.
    Works with the LangGraph TypedDict state pattern: receives full state,
    returns only the keys that changed.

    Flow:
        1. Create LLM client based on config (Anthropic or OpenAI)
        2. Build a prompt with paper text + analysis instructions
        3. Send to LLM, get back XML-tagged response
        4. Parse XML tags into a dict of analysis fields

    Args:
        state: PaperState TypedDict with full_text and metadata filled.

    Returns:
        Dict with analysis field updates (summary, methods, results, etc.)
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
    metadata = state.get("metadata", {})
    full_text = state.get("full_text", "")
    language = state.get("language", "zh")
    prompt = _build_prompt_from_dict(metadata, full_text, language)
    console.print(
        f"  [dim]Prompt length: {len(prompt):,} chars "
        f"(paper text: {len(full_text):,} chars)[/dim]"
    )

    # Step 3: Call LLM
    console.print("  [cyan]Calling LLM...[/cyan]")
    response = llm.invoke(prompt)

    # LangChain returns AIMessage; extract the text content
    content = response.content if hasattr(response, "content") else str(response)
    console.print(f"  [dim]Response length: {len(content):,} chars[/dim]")

    # Step 4: Parse response into update dict
    updates = _parse_response_to_dict(content)

    console.print("  [green]Analysis complete[/green]")
    return updates


# ---------------------------------------------------------------------------
# Prompt construction (dict-based, for LangGraph state)
# ---------------------------------------------------------------------------
def _build_prompt_from_dict(
    metadata: dict[str, Any],
    full_text: str,
    language: str,
) -> str:
    """Build the analysis prompt from metadata dict and text.

    Same logic as _build_prompt but works with plain dicts instead of
    PaperState dataclass (for LangGraph TypedDict compatibility).
    """
    text = _truncate_text(full_text, MAX_TEXT_CHARS)

    meta_lines = [f"Title: {metadata.get('title', '')}"]
    if metadata.get("authors"):
        meta_lines.append(f"Authors: {', '.join(metadata['authors'])}")
    if metadata.get("journal"):
        meta_lines.append(f"Journal: {metadata['journal']}")
    if metadata.get("year"):
        meta_lines.append(f"Year: {metadata['year']}")
    if metadata.get("doi"):
        meta_lines.append(f"DOI: {metadata['doi']}")
    metadata_block = "\n".join(meta_lines)

    if language == "zh":
        lang_instruction = (
            "请用中文输出分析结果。专业术语保留英文原文，"
            "首次出现时在括号中给出中文翻译，例如：SICM（扫描离子电导显微镜）。"
            "语言风格要通俗易懂，像在给同领域的研究生讲解。"
        )
    else:
        lang_instruction = (
            "Write the analysis in English. "
            "Keep technical terms precise and explain them briefly on first use."
        )

    prompt = f"""You are a scientific paper analysis assistant. Your job is to read a research paper and produce a structured analysis.

{lang_instruction}

<paper_metadata>
{metadata_block}
</paper_metadata>

<paper_text>
{text}
</paper_text>

Please analyze this paper and provide the following sections. Each section MUST be wrapped in the corresponding XML tag. Write substantive content for each section — not just one sentence.

<output_format>
<summary>
A concise paragraph (3-5 sentences) summarizing the paper's core contribution, methodology, and key findings. This should give a reader a complete picture without reading the full paper.
</summary>

<abstract_zh>
{"将论文摘要翻译成中文。如果论文没有明确的摘要段落，根据内容撰写一段中文摘要。" if language == "zh" else "Translate or rewrite the abstract in the target language."}
</abstract_zh>

<framework>
Describe the overall research framework/approach. What is the logical flow from problem to solution? Use a structured outline if helpful.
</framework>

<research_question>
What specific question(s) or problem(s) does this paper address? Why is it important? What gap in existing knowledge does it fill?
</research_question>

<methods>
Describe the methodology in detail. Include experimental setup, techniques used, data analysis approaches. For experimental papers, mention key instruments and protocols.
</methods>

<parameters>
If this is an experimental paper, list key experimental parameters as key-value pairs, one per line, in the format "parameter_name: value". For example:
Probe aperture: ~100 nm
Electrolyte: 50 mM KCl
If no specific parameters are mentioned, write "N/A".
</parameters>

<results>
Summarize the key findings. Use numbered points for clarity. Include quantitative data where available.
</results>

<innovations>
What are the novel contributions of this paper? What makes it different from prior work?
</innovations>

<limitations>
What are the limitations of this study? What could be improved? What questions remain unanswered?
</limitations>

<key_references>
List 3-8 of the most important references cited in this paper that a reader should follow up on. For each, provide the full citation as it appears in the paper. Focus on:
- Foundational methods papers
- Direct predecessors to this work
- Key competing approaches
</key_references>
</output_format>

IMPORTANT: Output ONLY the XML tags with content. Do not add any text before or after the tags."""

    return prompt


def _parse_response_to_dict(content: str) -> dict[str, Any]:
    """Parse XML-tagged LLM response into a dict of state updates.

    Returns a dict suitable for merging into PaperState TypedDict.
    """
    updates: dict[str, Any] = {}

    field_map = {
        "summary": "summary",
        "abstract_zh": "abstract_zh",
        "framework": "framework",
        "research_question": "research_question",
        "methods": "methods",
        "results": "results",
        "innovations": "innovations",
        "limitations": "limitations",
    }

    for tag, key in field_map.items():
        value = _extract_tag(content, tag)
        if value:
            updates[key] = value

    # Special: parameters → dict
    params_text = _extract_tag(content, "parameters")
    if params_text and params_text.strip().upper() != "N/A":
        updates["parameters"] = _parse_parameters(params_text)

    # Special: key_references → list
    refs_text = _extract_tag(content, "key_references")
    if refs_text:
        updates["key_references"] = _parse_references(refs_text)

    return updates


# ---------------------------------------------------------------------------
# LLM factory — creates the right client based on config
# ---------------------------------------------------------------------------
def _create_llm():
    """Create a LangChain chat model based on config.

    Supports two providers:
    - "anthropic": Uses ChatAnthropic (Claude)
    - "openai": Uses ChatOpenAI (GPT-4, etc.)

    The provider, model, temperature, and max_tokens are all
    configured in config.py (can be overridden via env vars).
    """
    provider = config.llm.provider
    api_key = config.llm.api_key

    env_var_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }

    if not api_key:
        env_var = env_var_map.get(provider, "API_KEY")
        raise RuntimeError(
            f"No API key found for provider '{provider}'. "
            f"Set {env_var} in your environment or .env file."
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=api_key,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=api_key,
        )
    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported: 'anthropic', 'openai', 'deepseek'"
        )


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def _build_prompt(state: "PaperState") -> str:
    """Build the analysis prompt from paper state.

    The prompt has three parts:
    1. System instruction — role, output format, language rules
    2. Paper metadata — title, authors, journal (gives context)
    3. Paper full text — truncated if too long

    Why XML output format?
    - Claude is trained on XML and handles it very reliably
    - Easy to parse with regex (no JSON escaping issues)
    - Allows natural long-form text within each tag
    """
    # Truncate text if too long (keep beginning + end for intro/conclusion)
    text = _truncate_text(state.full_text, MAX_TEXT_CHARS)

    # Build metadata context
    meta_lines = [f"Title: {state.metadata.title}"]
    if state.metadata.authors:
        meta_lines.append(f"Authors: {', '.join(state.metadata.authors)}")
    if state.metadata.journal:
        meta_lines.append(f"Journal: {state.metadata.journal}")
    if state.metadata.year:
        meta_lines.append(f"Year: {state.metadata.year}")
    if state.metadata.doi:
        meta_lines.append(f"DOI: {state.metadata.doi}")
    metadata_block = "\n".join(meta_lines)

    # Language instruction
    if state.language == "zh":
        lang_instruction = (
            "请用中文输出分析结果。专业术语保留英文原文，"
            "首次出现时在括号中给出中文翻译，例如：SICM（扫描离子电导显微镜）。"
            "语言风格要通俗易懂，像在给同领域的研究生讲解。"
        )
    else:
        lang_instruction = (
            "Write the analysis in English. "
            "Keep technical terms precise and explain them briefly on first use."
        )

    prompt = f"""You are a scientific paper analysis assistant. Your job is to read a research paper and produce a structured analysis.

{lang_instruction}

<paper_metadata>
{metadata_block}
</paper_metadata>

<paper_text>
{text}
</paper_text>

Please analyze this paper and provide the following sections. Each section MUST be wrapped in the corresponding XML tag. Write substantive content for each section — not just one sentence.

<output_format>
<summary>
A concise paragraph (3-5 sentences) summarizing the paper's core contribution, methodology, and key findings. This should give a reader a complete picture without reading the full paper.
</summary>

<abstract_zh>
{"将论文摘要翻译成中文。如果论文没有明确的摘要段落，根据内容撰写一段中文摘要。" if state.language == "zh" else "Translate or rewrite the abstract in the target language."}
</abstract_zh>

<framework>
Describe the overall research framework/approach. What is the logical flow from problem to solution? Use a structured outline if helpful.
</framework>

<research_question>
What specific question(s) or problem(s) does this paper address? Why is it important? What gap in existing knowledge does it fill?
</research_question>

<methods>
Describe the methodology in detail. Include experimental setup, techniques used, data analysis approaches. For experimental papers, mention key instruments and protocols.
</methods>

<parameters>
If this is an experimental paper, list key experimental parameters as key-value pairs, one per line, in the format "parameter_name: value". For example:
Probe aperture: ~100 nm
Electrolyte: 50 mM KCl
If no specific parameters are mentioned, write "N/A".
</parameters>

<results>
Summarize the key findings. Use numbered points for clarity. Include quantitative data where available.
</results>

<innovations>
What are the novel contributions of this paper? What makes it different from prior work?
</innovations>

<limitations>
What are the limitations of this study? What could be improved? What questions remain unanswered?
</limitations>

<key_references>
List 3-8 of the most important references cited in this paper that a reader should follow up on. For each, provide the full citation as it appears in the paper. Focus on:
- Foundational methods papers
- Direct predecessors to this work
- Key competing approaches
</key_references>
</output_format>

IMPORTANT: Output ONLY the XML tags with content. Do not add any text before or after the tags."""

    return prompt


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------
def _parse_response(content: str, state: "PaperState") -> "PaperState":
    """Parse XML-tagged LLM response into PaperState fields.

    Uses regex to extract content between XML tags. This is robust
    because:
    - Each field has a unique tag name (no ambiguity)
    - Content can span multiple lines (re.DOTALL flag)
    - Missing tags are handled gracefully (field stays empty)

    The 'parameters' field gets special treatment: it's parsed from
    "key: value" lines into a dict.
    """
    # Simple fields: extract text between tags
    field_map = {
        "summary": "summary",
        "abstract_zh": "abstract_zh",
        "framework": "framework",
        "research_question": "research_question",
        "methods": "methods",
        "results": "results",
        "innovations": "innovations",
        "limitations": "limitations",
    }

    for tag, attr in field_map.items():
        value = _extract_tag(content, tag)
        if value:
            setattr(state, attr, value)

    # Special: parameters → dict
    params_text = _extract_tag(content, "parameters")
    if params_text and params_text.strip().upper() != "N/A":
        state.parameters = _parse_parameters(params_text)

    # Special: key_references → list
    refs_text = _extract_tag(content, "key_references")
    if refs_text:
        state.key_references = _parse_references(refs_text)

    return state


def _extract_tag(content: str, tag: str) -> str:
    """Extract text content between <tag> and </tag>.

    Returns empty string if tag not found.
    """
    pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_parameters(text: str) -> dict[str, str]:
    """Parse parameter lines like 'key: value' into a dict.

    Handles various formats:
    - "Probe aperture: ~100 nm"
    - "- Electrolyte: 50 mM KCl"  (with bullet)
    - "Scan mode — hopping mode"  (with dash)
    """
    params: dict[str, str] = {}
    for line in text.strip().splitlines():
        line = line.strip().lstrip("-•* ")
        # Try "key: value" format
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if key and value:
                params[key] = value
    return params


def _parse_references(text: str) -> list[str]:
    """Parse reference list from LLM output.

    Each reference is typically on its own line, possibly with
    a bullet point or number prefix.
    """
    refs: list[str] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove common prefixes: "- ", "1. ", "• ", etc.
        line = re.sub(r"^[\d]+[.)]\s*", "", line)
        line = line.lstrip("-•* ").strip()
        if len(line) > 10:  # Skip very short lines (likely noise)
            refs.append(line)
    return refs


# ---------------------------------------------------------------------------
# Text truncation
# ---------------------------------------------------------------------------
def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate paper text to fit within LLM context window.

    Strategy: if text exceeds max_chars, keep the first 80% and
    last 20%. This preserves the introduction (background, methods)
    and conclusion (results, discussion) while trimming the middle
    (detailed results that are often repetitive).

    Why 80/20? The introduction and methods sections are critical
    for understanding the paper. The conclusion summarizes findings.
    The middle often contains detailed data tables and figures
    descriptions that the LLM can infer from context.
    """
    if len(text) <= max_chars:
        return text

    # Keep first 80% and last 20%
    head_size = int(max_chars * 0.8)
    tail_size = max_chars - head_size

    head = text[:head_size]
    tail = text[-tail_size:]

    return (
        f"{head}\n\n"
        f"[... middle section truncated ({len(text) - max_chars:,} chars removed) ...]\n\n"
        f"{tail}"
    )
