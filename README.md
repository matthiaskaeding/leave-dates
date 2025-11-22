# Parental Leave Timeline

Streamlit app that helps families plan parental leave by visualizing the coverage of each parent and highlighting overlapping time at home after a child is born.

## Requirements
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- [just](https://github.com/casey/just) for repeatable commands

## Setup

Install project dependencies into your active environment with uv:

```bash
just setup
# runs: uv pip install -e .
```

## Running the app

```bash
just run
```

The UI asks for:
1. Newborn birth date.
2. Mother's leave plan: Interval 1 is fixed to start on the birth date for 6 weeks and is always labeled “Mandatory”. Interval 2 collects a start date/duration (whole weeks only), and an optional Interval 3 can be added and named if needed.
3. Father's leave plan (same structure as above).

The chart displays each interval, plus any overlap between the parents' leaves, so you can quickly spot coverage gaps or double-coverage opportunities.

### Save plans locally
After entering the intervals, click **Save plan for next time** to store the current inputs in `.streamlit/last_plan.json` (ignored by git). When you reopen the app, the saved plan auto-populates the form. Delete that file if you want to reset the saved values.

### Linting & formatting

Run Ruff formatting (check-only) and lint fixes via:

```bash
just lint
```

## Testing

Automated tests can live under `tests/`. Execute the suite with:

```bash
just test
```
