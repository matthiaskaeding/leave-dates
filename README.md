# Parental Leave Timeline

Streamlit app that helps families plan parental leave by visualizing the coverage of each parent and highlighting overlapping time at home after a child is born.

## Running the app

```bash
uv run streamlit run main.py
```
The UI asks for:
1. Newborn birth date.
2. Mother's leave plan: Block 1 is fixed to start on the birth date for 6 weeks and is always labeled “Mandatory”. Use **Add another block** to append as many additional blocks as needed; each new block defaults to starting right after the prior one and can be defined via whole-week duration or explicit end date. Every block label starts as “Block N” — edit that inline to something more descriptive (e.g., “Vacation”).
3. Father's leave plan (same structure as above).

The chart displays each block, plus any overlap between the parents' leaves, so you can quickly spot coverage gaps or double-coverage opportunities. Each block label defaults to “Block N (Parent)” but you can add custom names (e.g., “Block 2 (Vacation)”) via the optional name fields.

### Save plans locally
After entering the intervals, click **Save plan for next time** to store the current inputs in `.streamlit/last_plan.json` (ignored by git). When you reopen the app, the saved plan auto-populates the form. Delete that file if you want to reset the saved values.
