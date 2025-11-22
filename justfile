set shell := ["bash", "-lc"]

default: run

setup:
    pip install uv
    uv pip install -r pyproject.toml

run:
	uv run streamlit run main.py

test:
	pytest

lint:
	uv run ruff format
	uv run ruff check --fix
