# Repository Guidelines

## Tooling Workflow
- Manage Python dependencies exclusively with [uv](https://github.com/astral-sh/uv); run `just setup` (alias for `uv pip install -e .`) whenever `pyproject.toml` changes.
- Use [just](https://github.com/casey/just) to run local commands so every agent follows the same workflow. Consult `justfile` before introducing new scripts.
- Block 1 is immutable: it always starts on the birth date, lasts 6 weeks, and stays labeled “Block 1 (Mandatory)”. Every additional block is added via the **Add another block** button, defaults to starting after the previous block, and may be defined by a whole-week duration or a precise end date. Each block’s label defaults to “Block N”; users can edit the text to something descriptive and it will appear across the UI and saved plans.
- The “Save plan for next time” button writes `.streamlit/last_plan.json`. This file is gitignored; do not check it in or rely on it containing production data.

## Project Structure & Module Organization
`main.py` holds the Streamlit entry point plus supporting helpers. `pyproject.toml` stores metadata and dependencies consumed by uv, while `README.md` documents setup steps. Expand reusable logic inside a `leave_dates/` package as the project grows and mirror each module inside `tests/`. Add visual assets or fixtures under `assets/` and reference them with relative paths to keep Streamlit deployments portable.

## Build, Test, and Development Commands
- `just setup`: installs the project into the active environment via `uv pip install -e .`.
- `just run`: launches `streamlit run main.py` for local development; use `-server.headless true` if deploying remotely.
- `just test`: executes `pytest`; append `-- -k overlap` (for example) to forward flags directly to pytest.
- `just lint`: runs `ruff format --check` and `ruff check --fix` through uv; ensure this passes before raising a PR.
If new workflows emerge, prefer adding another `just` recipe instead of sharing ad-hoc commands.

## Coding Style & Naming Conventions
Stick to PEP 8 with four-space indentation, snake_case functions/variables, and CamelCase classes. Favor pathlib over os.path, keep functions small, and annotate public APIs with typing information. Use f-strings for formatting, and prefer list/dict comprehensions over manual loops when they remain readable. Before pushing, run `ruff format . && ruff check .` (install Ruff globally or into your uv-managed environment) and resolve warnings rather than suppressing them.

## Testing Guidelines
Store tests under `tests/`, mirroring the source layout (`tests/test_main.py`, `tests/utils/test_overlap.py`, etc.). Write descriptive test names such as `test_overlap_detects_partial_overlap`. Leverage pytest fixtures for date ranges or leave scenarios, and keep Streamlit-specific calls behind injectable helper functions so logic remains unit-testable. Aim for meaningful scenario coverage, especially around overlap detection edge cases.

## Commit & Pull Request Guidelines
Work on a dedicated feature branch and merge back to `main` with `git merge --squash` to keep history linear. Follow imperative, present-tense commit subjects under 72 characters (e.g., "Add overlap summary table"). Pull requests should explain motivation, link issues, list manual/automated test evidence (`just run`, `just test`), and attach screenshots or videos whenever the UI changes. Confirm the just/uv workflow succeeds before requesting review.

## Agent-Specific Notes
Avoid touching unrelated files, prefer incremental commits, and document any external data or secrets needed to reproduce a change. When introducing new tooling, update this guide plus the `justfile` so the workflow stays synchronized across contributors.
