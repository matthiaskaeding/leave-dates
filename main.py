from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

import altair as alt
import pandas as pd
import streamlit as st


@dataclass
class IntervalInput:
    start_offset_weeks: float
    duration_weeks: float


@dataclass
class LeaveRecord:
    parent: str
    label: str
    start: date
    end: date
    duration_weeks: float


def collect_interval_inputs(section_title: str, key_prefix: str) -> List[IntervalInput]:
    st.subheader(section_title)
    interval_count = st.radio(
        "How many leave intervals?",
        options=[1, 2],
        horizontal=True,
        key=f"{key_prefix}-interval-count",
    )
    intervals: List[IntervalInput] = []
    for idx in range(1, interval_count + 1):
        cols = st.columns(2)
        with cols[0]:
            start_offset = st.number_input(
                f"Interval {idx} start offset (weeks from birth)",
                min_value=0.0,
                step=0.5,
                key=f"{key_prefix}-start-{idx}",
                help="Use 0 for leave that begins on the birth date.",
            )
        with cols[1]:
            duration = st.number_input(
                f"Interval {idx} duration (weeks)",
                min_value=0.0,
                step=0.5,
                key=f"{key_prefix}-duration-{idx}",
            )
        intervals.append(IntervalInput(start_offset, duration))
    return intervals


def build_records(
    parent_label: str, birth_date: date, intervals: List[IntervalInput]
) -> List[LeaveRecord]:
    records: List[LeaveRecord] = []
    for idx, interval in enumerate(intervals, 1):
        if interval.duration_weeks <= 0:
            continue
        start = birth_date + timedelta(days=interval.start_offset_weeks * 7)
        end = start + timedelta(days=interval.duration_weeks * 7)
        records.append(
            LeaveRecord(
                parent=parent_label,
                label=f"{parent_label} interval {idx}",
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

    birth_date = st.date_input("Date of birth", value=date.today())
    st.divider()
    mother_intervals = collect_interval_inputs("Mother's leave plan", "mother")
    st.divider()
    father_intervals = collect_interval_inputs("Father's leave plan", "father")

    mother_records = build_records("Mother", birth_date, mother_intervals)
    father_records = build_records("Father", birth_date, father_intervals)
    overlap_records = build_overlap_records(mother_records, father_records)
    all_records = mother_records + father_records + overlap_records

    st.divider()
    render_chart(all_records)


if __name__ == "__main__":
    main()
