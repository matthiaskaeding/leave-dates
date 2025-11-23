# Parental leave timeline

Streamlit app that helps families plan parental leave by visualizing the coverage of each parent and highlighting overlapping time at home after a child is born.

## Running the app

```bash
uv run streamlit run main.py
```
> Tip: `just run`, `just lint`, and `just test` are optional helpers around the same `uv` commands.
The UI asks for:
1. Newborn birth date.
2. Caregiver names: enter the two people who will take leave (defaults provided for quick experiments).
3. Caregiver plans: each caregiver gets an independent block planner. Use **Add block** to append as many leave blocks as required. Each block defaults to starting on the newborn’s birth date (or immediately after the previous block) and can be defined via a whole-week duration or an explicit end date. Every block label starts as “Block N,” but you can edit it inline to something descriptive (e.g., “Vacation”).

The chart displays each block, plus any overlap between the parents' leaves, so you can quickly spot coverage gaps or double-coverage opportunities. Custom labels appear everywhere (tooltips, chart legend, and table) once you rename a block.

### Import bank holidays
- Click **Import bank holidays (.ics)** to upload a calendar file (e.g., public holidays).
- Each event becomes a “Bank holidays” bar on the timeline so you can see overlaps with your leave plan.

### Save plans locally
After entering the intervals, click **Save plan for next time** to store the current inputs in `.streamlit/last_plan.json` (ignored by git). When you reopen the app, the saved plan auto-populates the form. Delete that file if you want to reset the saved values.
