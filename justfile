set shell := ["bash", "-lc"]

default: run

setup:
	uv pip install -e .

run:
	uv run streamlit run main.py

test:
	pytest

lint:
	uv run ruff format
	uv run ruff check --fix
