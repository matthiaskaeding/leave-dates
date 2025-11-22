set shell := ["bash", "-lc"]

default: run

run:
	uv run streamlit run main.py

test:
	pytest

lint:
	uv run ruff format --check
	uv run ruff check --fix
