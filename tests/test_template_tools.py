"""Tests for template rendering tools."""

from pathlib import Path

from paperpilot.tools.template_tools import list_templates, render_note, save_note


class TestRenderNote:
    def test_renders_paper_note(self) -> None:
        data = {
            "title": "Test Paper Title",
            "authors": ["Alice", "Bob"],
            "journal": "Nature",
            "year": "2024",
            "doi": "10.1234/test",
            "summary": "This paper does X.",
            "abstract_zh": "这篇论文做了X。",
            "framework": "提出问题 → 实验 → 结论",
            "research_question": "How does X affect Y?",
            "methods": "Used method A and B.",
            "parameters": {"孔径": "100 nm", "扫描模式": "hopping"},
            "results": "Found that X increases Y.",
            "innovations": "First to show X.",
            "limitations": "Small sample size.",
            "figures_markdown": "",
            "references": ["Ref 1", "Ref 2"],
        }
        result = render_note("paper_note.md.j2", data)

        assert "# Test Paper Title" in result
        assert "Alice, Bob" in result
        assert "This paper does X." in result
        assert "这篇论文做了X。" in result
        assert "100 nm" in result
        assert "Ref 1" in result

    def test_renders_without_optional_fields(self) -> None:
        data = {
            "title": "Minimal Paper",
            "authors": [],
            "journal": "",
            "year": "",
            "doi": "",
            "summary": "Summary.",
            "abstract_zh": "摘要。",
            "framework": "框架。",
            "research_question": "问题。",
            "methods": "方法。",
            "parameters": {},
            "results": "结果。",
            "innovations": "创新。",
            "limitations": "局限。",
            "figures_markdown": "",
            "references": [],
        }
        result = render_note("paper_note.md.j2", data)
        assert "# Minimal Paper" in result
        # Should not contain empty sections
        assert "关键实验参数" not in result


class TestSaveNote:
    def test_saves_to_file(self, tmp_path: Path) -> None:
        content = "# Test Note\nSome content."
        output = tmp_path / "subdir" / "test.md"
        result = save_note(content, output)

        assert result.exists()
        assert result.read_text(encoding="utf-8") == content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        output = tmp_path / "a" / "b" / "c" / "note.md"
        save_note("content", output)
        assert output.exists()


class TestListTemplates:
    def test_finds_builtin_templates(self) -> None:
        templates = list_templates()
        assert "paper_note.md.j2" in templates
        assert "comparison.md.j2" in templates
