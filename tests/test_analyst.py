"""Tests for the Analyst Agent (no real API calls).

Tests three layers:
1. Prompt construction — correct structure, metadata inclusion, truncation
2. Response parsing — XML tag extraction, parameter dict, reference list
3. Error handling — missing tags, malformed input, graceful degradation
"""

from pathlib import Path

import pytest

from paperpilot.agents.analyst import (
    _build_prompt_from_dict,
    _extract_tag,
    _parse_parameters,
    _parse_references,
    _parse_response_to_dict,
    _truncate_text,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_metadata() -> dict:
    """Realistic paper metadata dict for testing."""
    return {
        "title": "Nanoscale Surface Charge Visualization of Human Hair",
        "authors": ["Faduma M. Maddar", "David Perry", "Patrick R. Unwin"],
        "journal": "Analytical Chemistry",
        "year": "2019",
        "doi": "10.1021/acs.analchem.8b05977",
        "pages": 8,
        "abstract": "We present a method for nanoscale surface charge mapping...",
    }


@pytest.fixture
def sample_full_text() -> str:
    """Realistic paper text for testing."""
    return (
        "Introduction: Scanning ion conductance microscopy (SICM) is a "
        "powerful technique for imaging surface topography and charge. "
        "Methods: We used hopping mode SICM with 220 nm aperture probes. "
        "Results: The surface charge density of untreated hair was -15 mC/m². "
        "Conclusion: SICM enables nanoscale charge visualization of hair."
    )


@pytest.fixture
def sample_llm_response() -> str:
    """A realistic XML-tagged LLM response for parsing tests."""
    return """<summary>
本文首次使用 SICM（扫描离子电导显微镜）实现了人类头发表面电荷密度的纳米级定量可视化。
通过 hopping mode 结合电位脉冲计时电流法，在液相环境中同步获取形貌和电荷信息。
研究揭示了漂白和护发素处理对毛鳞片表面电荷分布的显著影响。
</summary>

<abstract_zh>
我们提出了一种纳米尺度表面电荷成像方法，基于扫描离子电导显微镜（SICM）的跳跃模式，
结合有限元模拟（FEM）将电流信号定量转化为表面电荷密度。
</abstract_zh>

<framework>
问题定义 → 方法设计（SICM + FEM）→ 验证实验（三组对比）→ 定量分析
</framework>

<research_question>
如何在液相环境中对头发表面电荷进行高分辨率定量 mapping？
传统方法（zeta 电位、KPFM）只能给出平均值或受环境干扰。
</research_question>

<methods>
SICM hopping mode + potential-pulse chronoamperometry，每个像素点同时获取形貌和电荷信息。
通过 FEM（有限元模拟，COMSOL Multiphysics）将归一化电流响应转换为定量的表面电荷密度。
</methods>

<parameters>
Probe aperture: ~220 nm
Electrolyte: 50 mM KCl
Scan mode: Hopping mode
Setpoint: 3% current drop
Potential pulse: +50 mV to -400 mV, 50 ms
</parameters>

<results>
1. 未处理头发：表面电荷密度约 -15 mC/m²
2. 漂白处理后：电荷增至 -100 mC/m²
3. 护发素处理后：电荷从负转正约 +5 mC/m²
</results>

<innovations>
- 首次实现头发表面电荷的纳米级定量成像
- SICM 在液相中工作，避免了 KPFM 的湿度问题
- 同步获取形貌+电荷
</innovations>

<limitations>
- 只测了一位供体的头发，样本代表性有限
- FEM 模型假设平面基底
- 扫描区域较小（~10×10 μm）
</limitations>

<key_references>
- Perry et al., JACS 2016 — SICM 形貌+电荷同步测量方法论文
- Kang et al., ACS Nano 2017 — hopping mode 速度和精度提升
- Page et al., Anal. Chem. 2016 — potential-pulse chronoamperometry 方法
</key_references>"""


# ---------------------------------------------------------------------------
# Prompt construction tests
# ---------------------------------------------------------------------------
class TestBuildPrompt:
    def test_contains_paper_text(self, sample_metadata: dict, sample_full_text: str) -> None:
        prompt = _build_prompt_from_dict(sample_metadata, sample_full_text, "zh")
        assert "hopping mode SICM" in prompt
        assert "220 nm aperture" in prompt

    def test_contains_metadata(self, sample_metadata: dict, sample_full_text: str) -> None:
        prompt = _build_prompt_from_dict(sample_metadata, sample_full_text, "zh")
        assert "Nanoscale Surface Charge" in prompt
        assert "Analytical Chemistry" in prompt
        assert "2019" in prompt

    def test_contains_xml_tags(self, sample_metadata: dict, sample_full_text: str) -> None:
        prompt = _build_prompt_from_dict(sample_metadata, sample_full_text, "zh")
        assert "<summary>" in prompt
        assert "<methods>" in prompt
        assert "<parameters>" in prompt
        assert "<key_references>" in prompt

    def test_chinese_instructions_for_zh(self, sample_metadata: dict, sample_full_text: str) -> None:
        prompt = _build_prompt_from_dict(sample_metadata, sample_full_text, "zh")
        assert "中文" in prompt
        assert "通俗易懂" in prompt

    def test_english_instructions_for_en(self, sample_metadata: dict, sample_full_text: str) -> None:
        prompt = _build_prompt_from_dict(sample_metadata, sample_full_text, "en")
        assert "English" in prompt


# ---------------------------------------------------------------------------
# XML tag extraction tests
# ---------------------------------------------------------------------------
class TestExtractTag:
    def test_basic_extraction(self) -> None:
        content = "<summary>This is a summary.</summary>"
        assert _extract_tag(content, "summary") == "This is a summary."

    def test_multiline_extraction(self) -> None:
        content = "<methods>\nLine 1\nLine 2\nLine 3\n</methods>"
        result = _extract_tag(content, "methods")
        assert "Line 1" in result
        assert "Line 3" in result

    def test_missing_tag_returns_empty(self) -> None:
        content = "<summary>Hello</summary>"
        assert _extract_tag(content, "methods") == ""

    def test_strips_whitespace(self) -> None:
        content = "<summary>  \n  Hello world  \n  </summary>"
        assert _extract_tag(content, "summary") == "Hello world"


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------
class TestParseResponse:
    def test_all_fields_populated(self, sample_llm_response: str) -> None:
        result = _parse_response_to_dict(sample_llm_response)
        assert "SICM" in result["summary"]
        assert "纳米" in result["abstract_zh"]
        assert "FEM" in result["framework"]
        assert "液相" in result["research_question"]
        assert "hopping mode" in result["methods"]
        assert "-15 mC/m²" in result["results"]
        assert "首次" in result["innovations"]
        assert "样本" in result["limitations"]

    def test_parameters_parsed_as_dict(self, sample_llm_response: str) -> None:
        result = _parse_response_to_dict(sample_llm_response)
        assert isinstance(result["parameters"], dict)
        assert "Probe aperture" in result["parameters"]
        assert result["parameters"]["Probe aperture"] == "~220 nm"
        assert result["parameters"]["Electrolyte"] == "50 mM KCl"

    def test_references_parsed_as_list(self, sample_llm_response: str) -> None:
        result = _parse_response_to_dict(sample_llm_response)
        assert isinstance(result["key_references"], list)
        assert len(result["key_references"]) == 3
        assert any("Perry" in ref for ref in result["key_references"])

    def test_partial_response_handled(self) -> None:
        """If LLM only returns some tags, only those keys are in the dict."""
        partial = "<summary>Just a summary.</summary><methods>Some methods.</methods>"
        result = _parse_response_to_dict(partial)
        assert result["summary"] == "Just a summary."
        assert result["methods"] == "Some methods."
        assert "framework" not in result
        assert "results" not in result

    def test_empty_response_handled(self) -> None:
        """Empty response returns empty dict."""
        result = _parse_response_to_dict("")
        assert result == {}


# ---------------------------------------------------------------------------
# Parameter parsing tests
# ---------------------------------------------------------------------------
class TestParseParameters:
    def test_basic_key_value(self) -> None:
        text = "Aperture: 220 nm\nElectrolyte: 50 mM KCl"
        params = _parse_parameters(text)
        assert params["Aperture"] == "220 nm"
        assert params["Electrolyte"] == "50 mM KCl"

    def test_bullet_prefix_stripped(self) -> None:
        text = "- Aperture: 220 nm\n- Mode: Hopping"
        params = _parse_parameters(text)
        assert "Aperture" in params
        assert "Mode" in params

    def test_na_returns_empty(self) -> None:
        """N/A parameters should be handled by the caller, not this function."""
        text = "N/A"
        params = _parse_parameters(text)
        # "N/A" has no colon, so nothing is parsed
        assert params == {}

    def test_empty_input(self) -> None:
        assert _parse_parameters("") == {}


# ---------------------------------------------------------------------------
# Reference parsing tests
# ---------------------------------------------------------------------------
class TestParseReferences:
    def test_bullet_list(self) -> None:
        text = "- Perry et al., JACS 2016\n- Kang et al., ACS Nano 2017"
        refs = _parse_references(text)
        assert len(refs) == 2
        assert "Perry" in refs[0]

    def test_numbered_list(self) -> None:
        text = "1. Perry et al., JACS 2016\n2. Kang et al., ACS Nano 2017"
        refs = _parse_references(text)
        assert len(refs) == 2

    def test_short_lines_skipped(self) -> None:
        text = "- Perry et al., JACS 2016\n- \n- OK"
        refs = _parse_references(text)
        assert len(refs) == 1  # Only the first line is long enough

    def test_empty_input(self) -> None:
        assert _parse_references("") == []


# ---------------------------------------------------------------------------
# Text truncation tests
# ---------------------------------------------------------------------------
class TestTruncateText:
    def test_short_text_unchanged(self) -> None:
        text = "Short paper text."
        assert _truncate_text(text, 1000) == text

    def test_long_text_truncated(self) -> None:
        text = "A" * 200
        result = _truncate_text(text, 100)
        assert len(result) < 200
        assert "truncated" in result

    def test_preserves_head_and_tail(self) -> None:
        text = "INTRO_" + "X" * 200 + "_CONCLUSION"
        result = _truncate_text(text, 100)
        assert "INTRO_" in result
        assert "_CONCLUSION" in result
