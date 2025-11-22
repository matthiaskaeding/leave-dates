from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

import altair as alt
import pandas as pd
import streamlit as st

DEFAULT_INTERVAL_WEEKS = 6
PLAN_PATH = Path(".streamlit/last_plan.json")


@dataclass
class IntervalInput:
    start_date: date
    duration_weeks: float
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date.isoformat(),
            "duration_weeks": float(self.duration_weeks),
            "name": self.name,
        }


@dataclass
class LeaveRecord:
    parent: str
    label: str
    start: date
    end: date
    duration_weeks: float


def duration_weeks_to_days(duration_weeks: float) -> int:
    return max(int(round(duration_weeks * 7)), 0)


def compute_inclusive_end(start: date, duration_weeks: float) -> date:
    total_days = duration_weeks_to_days(duration_weeks)
    if total_days <= 0:
        return start
    return start + timedelta(days=total_days - 1)


def rerun_app() -> None:
    rerun_fn = getattr(st, "rerun", None)
    if callable(rerun_fn):
        rerun_fn()
    else:
        legacy = getattr(st, "experimental_rerun", None)
        if callable(legacy):
            legacy()


def interval_from_dict(data: Dict[str, Any]) -> IntervalInput:
    start = date.fromisoformat(data["start_date"])
    duration = float(data.get("duration_weeks", 0))
    name = data.get("name")
    return IntervalInput(start, duration, name)


def load_saved_plan() -> Optional[Dict[str, Any]]:
    if not PLAN_PATH.exists():
        return None
    try:
        raw = json.loads(PLAN_PATH.read_text())
        birth_date = date.fromisoformat(raw["birth_date"])
        return {
            "birth_date": birth_date,
            "mother": [interval_from_dict(item) for item in raw.get("mother", [])],
            "father": [interval_from_dict(item) for item in raw.get("father", [])],
        }
    except Exception:
        st.warning("Saved plan could not be read. Starting with defaults.")
        return None


def save_plan(
    birth_date: date,
    mother_intervals: List[IntervalInput],
    father_intervals: List[IntervalInput],
) -> None:
    payload = {
        "birth_date": birth_date.isoformat(),
        "mother": [interval.to_dict() for interval in mother_intervals],
        "father": [interval.to_dict() for interval in father_intervals],
    }
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(payload, indent=2))


def collect_interval_inputs(
    section_title: str,
    key_prefix: str,
    birth_date: date,
    saved_intervals: Optional[List[IntervalInput]] = None,
) -> List[IntervalInput]:
    st.subheader(section_title)
    intervals: List[IntervalInput] = []

    st.info(
        f"Block 1 (Mandatory) starts on {birth_date.isoformat()} and lasts "
        f"{DEFAULT_INTERVAL_WEEKS} weeks."
    )
    intervals.append(
        IntervalInput(birth_date, DEFAULT_INTERVAL_WEEKS, "Block 1 (Mandatory)")
    )

    saved_extras = (
        saved_intervals[1:] if saved_intervals and len(saved_intervals) > 1 else []
    )
    state_key = f"{key_prefix}-blocks"
    if state_key not in st.session_state:
        st.session_state[state_key] = [
            saved_extras[idx] if idx < len(saved_extras) else None
            for idx in range(max(1, len(saved_extras)))
        ]
    blocks_state: List[Optional[IntervalInput]] = st.session_state[state_key]
    if st.button("Add another block", key=f"{key_prefix}-add-interval"):
        blocks_state.append(None)
    st.session_state[state_key] = blocks_state

    previous_start = birth_date
    previous_duration = DEFAULT_INTERVAL_WEEKS
    for idx, saved_interval in enumerate(blocks_state):
        interval_number = idx + 2
        name_default = (
            saved_interval.name if saved_interval and saved_interval.name else f"Block {interval_number}"
        )
        cols = st.columns((1.4, 1))
        with cols[0]:
            block_name = (
                st.text_input(
                    f"Block {interval_number} label",
                    value=name_default,
                    key=f"{key_prefix}-name-{interval_number}",
                    placeholder="e.g., Vacation",
                ).strip()
                or f"Block {interval_number}"
            )
        with cols[1]:
            default_start = (
                saved_interval.start_date
                if saved_interval
                else previous_start + timedelta(weeks=previous_duration)
            )
            interval_start = st.date_input(
                f"Block {interval_number} start date",
                value=default_start,
                key=f"{key_prefix}-start-date-{interval_number}",
            )
        default_duration = (
            saved_interval.duration_weeks if saved_interval else previous_duration
        )
        mode_index = 0
        if (
            saved_interval
            and saved_interval.duration_weeks
            and not float(saved_interval.duration_weeks).is_integer()
        ):
            mode_index = 1
        cols = st.columns(2)
        with cols[0]:
            mode = st.radio(
                "Specify by",
                ["Duration", "End date"],
                key=f"{key_prefix}-mode-{interval_number}",
                horizontal=True,
                index=mode_index,
            )
        with cols[1]:
            if mode == "Duration":
                duration_value = st.number_input(
                    "Duration (weeks)",
                    min_value=0,
                    step=1,
                    value=int(round(default_duration)) if default_duration else 0,
                    key=f"{key_prefix}-duration-{interval_number}",
                )
                interval_duration = float(duration_value)
            else:
                saved_end = (
                    compute_inclusive_end(saved_interval.start_date, saved_interval.duration_weeks)
                    if saved_interval
                    else compute_inclusive_end(
                        interval_start,
                        default_duration or DEFAULT_INTERVAL_WEEKS,
                    )
                )
                interval_end = st.date_input(
                    "End date",
                    value=saved_end,
                    min_value=interval_start,
                    key=f"{key_prefix}-end-date-{interval_number}",
                )
                interval_duration = max(
                    ((interval_end - interval_start).days + 1) / 7, 0.0
                )
        if len(blocks_state) > 1:
            if st.button(
                f"Delete block {interval_number}",
                key=f"{key_prefix}-delete-{interval_number}",
            ):
                del blocks_state[idx]
                rerun_app()
        intervals.append(
            IntervalInput(interval_start, interval_duration, block_name)
        )
        previous_start = interval_start
        previous_duration = interval_duration
    return intervals


def build_records(
    parent_label: str, intervals: List[IntervalInput]
) -> List[LeaveRecord]:
    records: List[LeaveRecord] = []
    for idx, interval in enumerate(intervals, 1):
        if interval.duration_weeks <= 0:
            continue
        start = interval.start_date
        end = compute_inclusive_end(start, interval.duration_weeks)
        label_name = interval.name or f"Block {idx}"
        label = f"{parent_label} {label_name}"
        records.append(
            LeaveRecord(
                parent=parent_label,
                label=label,
                start=start,
                end=end,
                duration_weeks=interval.duration_weeks,
            )
        )
    return records


def build_overlap_records(
    mother: List[LeaveRecord], father: List[LeaveRecord]
) -> List[LeaveRecord]:
    overlaps: List[LeaveRecord] = []
    for m in mother:
        for f in father:
            overlap_start = max(m.start, f.start)
            overlap_end = min(m.end, f.end)
            if overlap_start <= overlap_end:
                duration_days = (overlap_end - overlap_start).days + 1
                duration_weeks = duration_days / 7
                overlaps.append(
                    LeaveRecord(
                        parent="Overlap",
                        label=f"{m.label} ∩ {f.label}",
                        start=overlap_start,
                        end=overlap_end,
                        duration_weeks=duration_weeks,
                    )
                )
    return overlaps


def render_chart(records: List[LeaveRecord]) -> None:
    if not records:
        st.info("Add at least one leave interval to view the timeline.")
        return

    df = pd.DataFrame(
        [
            {
                "parent": record.parent,
                "label": record.label,
                "start": record.start,
                "end_inclusive": record.end,
                "end_exclusive": record.end + timedelta(days=1),
                "duration_weeks": record.duration_weeks,
            }
            for record in records
        ]
    )
    df["weeks"] = df["duration_weeks"].apply(lambda value: round(value, 1))
    df["days"] = df["duration_weeks"].apply(duration_weeks_to_days)

    parent_order = ["Mother", "Father", "Overlap"]
    used_parents = [p for p in parent_order if p in df["parent"].unique()]
    color_scale = alt.Scale(
        domain=used_parents,
        range=["#8fb339", "#3f88c5", "#f26419"][: len(used_parents)],
    )

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadius=4)
        .encode(
            x=alt.X("start:T", title="Calendar date"),
            x2="end_exclusive:T",
            y=alt.Y("parent:N", sort=used_parents, title=""),
            color=alt.Color("parent:N", scale=color_scale, legend=alt.Legend(title="")),
            tooltip=[
                alt.Tooltip("label:N", title="Block"),
                alt.Tooltip("start:T", title="Start"),
                alt.Tooltip("end_inclusive:T", title="End"),
                alt.Tooltip("weeks:Q", title="Weeks"),
                alt.Tooltip("days:Q", title="Days"),
            ],
        )
        .properties(height=180)
    )
    st.altair_chart(chart, use_container_width=True)
    table_df = df[["label", "start", "end_inclusive", "weeks", "days"]].rename(
        columns={"end_inclusive": "end"}
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Parental Leave Timeline", layout="centered")
    st.title("Parental Leave Timeline")
    st.caption(
        "Enter the newborn's birth date and leave intervals (in weeks) for each parent "
        "to visualize coverage and overlap."
    )

    saved_plan = load_saved_plan()
    default_birth = saved_plan["birth_date"] if saved_plan else date.today()
    birth_date = st.date_input("Date of birth", value=default_birth)
    if saved_plan:
        st.info("Loaded your previously saved plan from .streamlit/last_plan.json.")
    st.divider()

    mother_intervals = collect_interval_inputs(
        "Mother's leave plan",
        "mother",
        birth_date,
        saved_plan["mother"] if saved_plan else None,
    )
    st.divider()
    father_intervals = collect_interval_inputs(
        "Father's leave plan",
        "father",
        birth_date,
        saved_plan["father"] if saved_plan else None,
    )

    mother_records = build_records("Mother", mother_intervals)
    father_records = build_records("Father", father_intervals)
    overlap_records = build_overlap_records(mother_records, father_records)
    all_records = mother_records + father_records + overlap_records

    st.divider()
    render_chart(all_records)
    if st.button("Save plan for next time"):
        save_plan(birth_date, mother_intervals, father_intervals)
        st.success("Plan saved locally (.streamlit/last_plan.json).")


if __name__ == "__main__":
    main()
