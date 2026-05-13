"""Tests for the Compare Agent (no real API calls).

Tests three layers:
1. Prompt construction — correct structure, all papers included
2. Response parsing — XML extraction, fallback handling
3. Fallback comparison — metadata-only comparison when LLM unavailable
"""

import pytest

from paperpilot.agents.compare import (
    _build_compare_prompt,
    _derive_topic,
    _extract_field,
    _parse_compare_response,
    compare_papers_fallback,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def two_states() -> list[dict]:
    """Two state dicts with realistic data for comparison tests."""
    state1 = {
        "metadata": {
            "title": "Nanoscale Surface Charge Visualization of Human Hair",
            "authors": ["Faduma M. Maddar", "David Perry"],
            "journal": "Analytical Chemistry",
            "year": "2019",
            "doi": "10.1021/acs.analchem.8b05977",
            "pages": 8,
        },
        "research_question": "如何在液相环境中对头发表面电荷进行纳米级定量成像？",
        "methods": "SICM hopping mode + potential-pulse chronoamperometry",
        "results": "未处理头发约 -15 mC/m²，漂白后增至 -100 mC/m²",
        "innovations": "首次实现头发表面电荷的纳米级定量成像",
        "limitations": "只测了一位供体的头发",
    }

    state2 = {
        "metadata": {
            "title": "Surface Charge Visualization at Viable Living Cells",
            "authors": ["David Perry", "Ashley Page"],
            "journal": "JACS",
            "year": "2016",
            "doi": "10.1021/jacs.6b04065",
            "pages": 6,
        },
        "research_question": "如何对活细胞表面电荷进行纳米级成像？",
        "methods": "SICM hopping mode with bias modulation",
        "results": "成功对活细胞表面电荷进行了定量成像",
        "innovations": "首次在活细胞上实现 SICM 电荷成像",
        "limitations": "细胞活性维持时间有限",
    }

    return [state1, state2]


@pytest.fixture
def sample_compare_response() -> str:
    """A realistic XML-tagged comparison response."""
    return """<paper index="1">
<short_title>Maddar 2019</short_title>
<year>2019</year>
<research_question>液相环境中头发表面电荷的纳米级定量成像</research_question>
<methods_brief>SICM hopping mode + 电位脉冲计时电流法</methods_brief>
<results_brief>未处理头发 -15 mC/m²，漂白后 -100 mC/m²</results_brief>
<innovations_brief>首次实现头发表面电荷纳米级定量成像</innovations_brief>
<limitations_brief>单一供体样本</limitations_brief>
</paper>

<paper index="2">
<short_title>Perry 2016</short_title>
<year>2016</year>
<research_question>活细胞表面电荷的纳米级成像</research_question>
<methods_brief>SICM hopping mode + bias modulation</methods_brief>
<results_brief>成功对活细胞表面电荷定量成像</results_brief>
<innovations_brief>首次在活细胞上实现 SICM 电荷成像</innovations_brief>
<limitations_brief>细胞活性维持时间有限</limitations_brief>
</paper>

<analysis>
这两篇论文都使用 SICM 的 hopping mode 进行表面电荷成像，但应用对象不同：
Perry 2016 首先在活细胞上验证了方法可行性，Maddar 2019 将其扩展到头发样品。
从方法演进来看，Maddar 2019 增加了 FEM 定量转化步骤，使结果更加定量化。
</analysis>"""


# ---------------------------------------------------------------------------
# Prompt construction tests
# ---------------------------------------------------------------------------
class TestBuildComparePrompt:
    def test_contains_all_papers(self, two_states: list[dict]) -> None:
        prompt = _build_compare_prompt(two_states, "zh")
        assert "Nanoscale Surface Charge" in prompt
        assert "Viable Living Cells" in prompt

    def test_contains_paper_fields(self, two_states: list[dict]) -> None:
        prompt = _build_compare_prompt(two_states, "zh")
        assert "hopping mode" in prompt
        assert "-15 mC/m²" in prompt

    def test_contains_xml_structure(self, two_states: list[dict]) -> None:
        prompt = _build_compare_prompt(two_states, "zh")
        assert '<paper_input index="1">' in prompt
        assert '<paper_input index="2">' in prompt
        assert "<analysis>" in prompt

    def test_chinese_instructions(self, two_states: list[dict]) -> None:
        prompt = _build_compare_prompt(two_states, "zh")
        assert "中文" in prompt

    def test_english_instructions(self, two_states: list[dict]) -> None:
        prompt = _build_compare_prompt(two_states, "en")
        assert "English" in prompt


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------
class TestParseCompareResponse:
    def test_parses_all_papers(self, sample_compare_response: str, two_states: list[dict]) -> None:
        result = _parse_compare_response(sample_compare_response, two_states)
        assert len(result["papers"]) == 2

    def test_paper_fields_populated(
        self, sample_compare_response: str, two_states: list[dict]
    ) -> None:
        result = _parse_compare_response(sample_compare_response, two_states)
        paper1 = result["papers"][0]
        assert paper1["short_title"] == "Maddar 2019"
        assert paper1["year"] == "2019"
        assert "头发" in paper1["research_question"]
        assert "hopping" in paper1["methods_brief"]

    def test_analysis_extracted(self, sample_compare_response: str, two_states: list[dict]) -> None:
        result = _parse_compare_response(sample_compare_response, two_states)
        assert "hopping mode" in result["analysis"]
        assert "Perry 2016" in result["analysis"]

    def test_partial_response_fills_fallback(self, two_states: list[dict]) -> None:
        """If only one paper is parsed, the other gets fallback data."""
        partial = """<paper index="1">
<short_title>Maddar 2019</short_title>
<year>2019</year>
<research_question>Test</research_question>
<methods_brief>Test</methods_brief>
<results_brief>Test</results_brief>
<innovations_brief>Test</innovations_brief>
<limitations_brief>Test</limitations_brief>
</paper>"""
        result = _parse_compare_response(partial, two_states)
        assert len(result["papers"]) == 2
        # Second paper should have fallback data
        assert result["papers"][1]["short_title"] == "Perry 2016"

    def test_empty_response(self, two_states: list[dict]) -> None:
        result = _parse_compare_response("", two_states)
        assert len(result["papers"]) == 2  # All fallback
        assert result["analysis"] == ""


# ---------------------------------------------------------------------------
# Fallback comparison tests
# ---------------------------------------------------------------------------
class TestComparepapersFallback:
    def test_returns_all_papers(self, two_states: list[dict]) -> None:
        result = compare_papers_fallback(two_states)
        assert len(result["papers"]) == 2

    def test_short_title_format(self, two_states: list[dict]) -> None:
        result = compare_papers_fallback(two_states)
        assert result["papers"][0]["short_title"] == "Maddar 2019"
        assert result["papers"][1]["short_title"] == "Perry 2016"

    def test_truncates_long_fields(self, two_states: list[dict]) -> None:
        two_states[0]["methods"] = "A" * 200
        result = compare_papers_fallback(two_states)
        assert len(result["papers"][0]["methods_brief"]) < 200
        assert result["papers"][0]["methods_brief"].endswith("...")

    def test_has_generated_at(self, two_states: list[dict]) -> None:
        result = compare_papers_fallback(two_states)
        assert "generated_at" in result


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------
class TestExtractField:
    def test_basic(self) -> None:
        assert _extract_field("<year>2019</year>", "year") == "2019"

    def test_missing(self) -> None:
        assert _extract_field("<year>2019</year>", "title") == ""

    def test_multiline(self) -> None:
        content = "<analysis>\nLine 1\nLine 2\n</analysis>"
        result = _extract_field(content, "analysis")
        assert "Line 1" in result
        assert "Line 2" in result


class TestDeriveTopic:
    def test_uses_first_title(self, two_states: list[dict]) -> None:
        topic = _derive_topic(two_states)
        assert "Nanoscale" in topic

    def test_truncates_long_title(self, two_states: list[dict]) -> None:
        two_states[0]["metadata"]["title"] = "A" * 100
        topic = _derive_topic(two_states)
        assert len(topic) <= 60

    def test_empty_states(self) -> None:
        assert _derive_topic([]) == "Paper Comparison"
