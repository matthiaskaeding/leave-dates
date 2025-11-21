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
2. Mother's leave plan (one or two intervals, each defined by the start offset in weeks relative to the birth date and the interval length).
3. Father's leave plan (same structure as above).

The chart displays each interval, plus any overlap between the parents' leaves, so you can quickly spot coverage gaps or double-coverage opportunities.

## Testing

Automated tests can live under `tests/`. Execute the suite with:

```bash
just test
```
