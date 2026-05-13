.PHONY: demo install test lint format clean

# Quick demo — runs without API key (metadata-only mode)
demo:
	@echo "🚀 Running PaperPilot demo..."
	@echo ""
	uv run paperpilot read examples/sample.pdf -o examples/output/
	@echo ""
	@echo "✅ Done! Check examples/output/ for the generated note."

# Full demo — requires ANTHROPIC_API_KEY (or other LLM provider)
demo-full:
	@echo "🚀 Running PaperPilot full analysis..."
	@echo ""
	uv run paperpilot read examples/sample.pdf -o examples/output/ --figures
	@echo ""
	@echo "✅ Done! Check examples/output/ for the generated note with LLM analysis."

install:
	uv sync

test:
	uv run pytest -v -k "not network"

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/

clean:
	rm -rf .pytest_cache __pycache__ .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
