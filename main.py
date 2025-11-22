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
            "duration_weeks": int(self.duration_weeks),
            "name": self.name,
        }


@dataclass
class LeaveRecord:
    parent: str
    label: str
    start: date
    end: date
    duration_weeks: float


def interval_from_dict(data: Dict[str, Any]) -> IntervalInput:
    start = date.fromisoformat(data["start_date"])
    duration = int(data.get("duration_weeks", 0))
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

    st.markdown(
        f"**Interval 1**: fixed at the birth date ({birth_date.isoformat()}) "
        f"for {DEFAULT_INTERVAL_WEEKS} weeks and always labeled **Mandatory**."
    )
    intervals.append(IntervalInput(birth_date, DEFAULT_INTERVAL_WEEKS, "Mandatory"))

    second_default = (
        saved_intervals[1] if saved_intervals and len(saved_intervals) > 1 else None
    )
    st.markdown("**Interval 2**")
    interval_two_start = st.date_input(
        "Start date",
        value=second_default.start_date
        if second_default
        else birth_date + timedelta(weeks=DEFAULT_INTERVAL_WEEKS),
        key=f"{key_prefix}-start-date-2",
    )
    second_duration_default = (
        int(second_default.duration_weeks) if second_default else 0
    )
    interval_two_duration = st.number_input(
        "Duration (weeks)",
        min_value=0,
        step=1,
        value=second_duration_default,
        key=f"{key_prefix}-duration-2",
    )
    interval_two_name = st.text_input(
        "Interval 2 name (optional)",
        value=second_default.name if second_default and second_default.name else "",
        key=f"{key_prefix}-name-2",
        placeholder="e.g., Part-time block",
    )
    intervals.append(
        IntervalInput(
            interval_two_start,
            interval_two_duration,
            interval_two_name or None,
        )
    )

    third_default = (
        saved_intervals[2] if saved_intervals and len(saved_intervals) > 2 else None
    )
    third_duration_default = int(third_default.duration_weeks) if third_default else 0
    add_third = st.checkbox(
        "Add a third interval?",
        value=bool(third_default and third_duration_default > 0),
        key=f"{key_prefix}-third-toggle",
        help="Leave unchecked if only two leave blocks are planned.",
    )
    if add_third:
        default_third_start = (
            third_default.start_date
            if third_default
            else interval_two_start + timedelta(weeks=interval_two_duration)
        )
        interval_three_start = st.date_input(
            "Interval 3 start date",
            value=default_third_start,
            key=f"{key_prefix}-start-date-3",
        )
        interval_three_duration = st.number_input(
            "Interval 3 duration (weeks)",
            min_value=0,
            step=1,
            value=third_duration_default,
            key=f"{key_prefix}-duration-3",
        )
        interval_three_name = st.text_input(
            "Interval 3 name (optional)",
            value=third_default.name if third_default and third_default.name else "",
            key=f"{key_prefix}-name-3",
            placeholder="e.g., Transition period",
        )
        intervals.append(
            IntervalInput(
                interval_three_start,
                interval_three_duration,
                interval_three_name or None,
            )
        )
    return intervals


def build_records(
    parent_label: str, intervals: List[IntervalInput]
) -> List[LeaveRecord]:
    records: List[LeaveRecord] = []
    for idx, interval in enumerate(intervals, 1):
        if interval.duration_weeks <= 0:
            continue
        start = interval.start_date
        end = start + timedelta(days=interval.duration_weeks * 7)
        label = interval.name or f"{parent_label} interval {idx}"
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
            if overlap_start < overlap_end:
                duration_weeks = (overlap_end - overlap_start).days / 7
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
                "end": record.end,
                "duration_weeks": record.duration_weeks,
            }
            for record in records
        ]
    )

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
            x2="end:T",
            y=alt.Y("parent:N", sort=used_parents, title=""),
            color=alt.Color("parent:N", scale=color_scale, legend=alt.Legend(title="")),
            tooltip=["label", "start", "end", "duration_weeks"],
        )
        .properties(height=180)
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(
        df[["label", "start", "end", "duration_weeks"]],
        use_container_width=True,
        hide_index=True,
    )


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
