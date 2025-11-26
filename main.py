from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import streamlit as st
from icalendar import Calendar

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

        def parse_intervals(*keys: str) -> List[IntervalInput]:
            for key in keys:
                if key in raw:
                    return [interval_from_dict(item) for item in raw.get(key, [])]
            return []

        holidays: List[LeaveRecord] = []
        for entry in raw.get("holidays", []):
            start = date.fromisoformat(entry["start"])
            end = date.fromisoformat(entry["end"])
            duration_weeks = ((end - start).days + 1) / 7
            holidays.append(
                LeaveRecord(
                    parent="Bank holidays",
                    label=entry.get("label", "Holiday"),
                    start=start,
                    end=end,
                    duration_weeks=duration_weeks,
                )
            )

        return {
            "birth_date": birth_date,
            "caregiver-a": parse_intervals("caregiver-a", "mother"),
            "caregiver-b": parse_intervals("caregiver-b", "father"),
            "caregiver_a_name": raw.get(
                "caregiver_a_name", raw.get("mother_name", "Caregiver 1")
            ),
            "caregiver_b_name": raw.get(
                "caregiver_b_name", raw.get("father_name", "Caregiver 2")
            ),
            "holidays": holidays,
        }
    except Exception:
        st.warning("Saved plan could not be read. Starting with defaults.")
        return None


def save_plan(
    birth_date: date,
    caregiver_a_intervals: List[IntervalInput],
    caregiver_b_intervals: List[IntervalInput],
    caregiver_a_name: str,
    caregiver_b_name: str,
    holidays: List[LeaveRecord],
) -> None:
    payload = {
        "birth_date": birth_date.isoformat(),
        "caregiver-a": [interval.to_dict() for interval in caregiver_a_intervals],
        "caregiver-b": [interval.to_dict() for interval in caregiver_b_intervals],
        "caregiver_a_name": caregiver_a_name,
        "caregiver_b_name": caregiver_b_name,
        "holidays": [
            {
                "label": holiday.label,
                "start": holiday.start.isoformat(),
                "end": holiday.end.isoformat(),
            }
            for holiday in holidays
        ],
    }
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps(payload, indent=2))


def parse_bank_holidays(uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]) -> List[LeaveRecord]:
    if not uploaded_file:
        return []
    try:
        calendar = Calendar.from_ical(uploaded_file.getvalue())
    except Exception:
        st.warning("Unable to read the provided .ics file.")
        return []

    def _to_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.today()

    records: List[LeaveRecord] = []
    for idx, component in enumerate(calendar.walk("VEVENT")):
        start_component = component.get("dtstart")
        if not start_component:
            continue
        start_date = _to_date(component.decoded("dtstart"))

        end_component = component.get("dtend")
        if end_component:
            end_date = _to_date(component.decoded("dtend"))
            if end_date > start_date:
                end_date = end_date - timedelta(days=1)
        else:
            end_date = start_date

        if end_date < start_date:
            end_date = start_date
        duration_weeks = ((end_date - start_date).days + 1) / 7
        summary = str(component.get("summary", f"Holiday {idx + 1}"))
        records.append(
            LeaveRecord(
                parent="Bank holidays",
                label=summary,
                start=start_date,
                end=end_date,
                duration_weeks=duration_weeks,
            )
        )
    return records


def holiday_lookup(holidays: List[LeaveRecord]) -> Dict[date, List[str]]:
    lookup: Dict[date, List[str]] = defaultdict(list)
    for holiday in holidays:
        current = holiday.start
        while current <= holiday.end:
            lookup[current].append(holiday.label)
            current += timedelta(days=1)
    return lookup


def collect_interval_inputs(
    section_title: str,
    key_prefix: str,
    birth_date: date,
    saved_intervals: Optional[List[IntervalInput]] = None,
) -> List[IntervalInput]:
    st.subheader(section_title)
    intervals: List[IntervalInput] = []

    state_key = f"{key_prefix}-blocks"
    if state_key not in st.session_state:
        st.session_state[state_key] = (
            list(saved_intervals) if saved_intervals else [None]
        )
    blocks_state: List[Optional[IntervalInput]] = st.session_state[state_key]
    if st.button("Add block", key=f"{key_prefix}-add-block"):
        blocks_state.append(None)
    st.session_state[state_key] = blocks_state

    previous_start = birth_date
    previous_duration = DEFAULT_INTERVAL_WEEKS
    for idx, saved_interval in enumerate(blocks_state):
        interval_number = idx + 1
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
            if saved_interval:
                default_start = saved_interval.start_date
            elif idx == 0:
                default_start = birth_date
            else:
                prev_end = compute_inclusive_end(previous_start, previous_duration)
                default_start = prev_end + timedelta(days=1)
            interval_start = st.date_input(
                f"Block {interval_number} start date",
                value=default_start,
                key=f"{key_prefix}-start-date-{interval_number}",
            )
        default_duration = (
            saved_interval.duration_weeks
            if saved_interval and saved_interval.duration_weeks
            else DEFAULT_INTERVAL_WEEKS
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
    caregiver_a: List[LeaveRecord], caregiver_b: List[LeaveRecord]
) -> List[LeaveRecord]:
    overlaps: List[LeaveRecord] = []
    for a_record in caregiver_a:
        for b_record in caregiver_b:
            overlap_start = max(a_record.start, b_record.start)
            overlap_end = min(a_record.end, b_record.end)
            if overlap_start <= overlap_end:
                duration_days = (overlap_end - overlap_start).days + 1
                duration_weeks = duration_days / 7
                overlaps.append(
                    LeaveRecord(
                        parent="Overlap",
                        label=f"{a_record.label} ∩ {b_record.label}",
                        start=overlap_start,
                        end=overlap_end,
                        duration_weeks=duration_weeks,
                    )
                )
    return overlaps


def render_chart(
    records: List[LeaveRecord],
    holidays: List[LeaveRecord],
    holiday_lookup_map: Dict[date, List[str]],
) -> None:
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

    def labels_for_block(row: pd.Series) -> List[str]:
        labels: set[str] = set()
        current = row["start"]
        while current <= row["end_inclusive"]:
            for label in holiday_lookup_map.get(current, []):
                labels.add(label)
            current += timedelta(days=1)
        return sorted(labels)

    def dates_for_block(row: pd.Series) -> List[str]:
        dates: List[date] = []
        current = row["start"]
        while current <= row["end_inclusive"]:
            if holiday_lookup_map.get(current):
                dates.append(current)
            current += timedelta(days=1)
        unique_dates = sorted(set(dates))
        return [d.isoformat() for d in unique_dates]

    df["holiday_dates"] = df.apply(dates_for_block, axis=1)
    df["holiday_count"] = df["holiday_dates"].apply(len)
    df["holiday_dates_display"] = df["holiday_dates"].apply(
        lambda dates: ", ".join(dates) if dates else "None"
    )

    parent_order = df["parent"].unique().tolist()
    used_parents = [p for p in parent_order if p in df["parent"].unique()]
    color_scale = alt.Scale(
        domain=used_parents,
        range=["#8fb339", "#3f88c5", "#f26419"][: len(used_parents)],
    )

    base_chart = (
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
                alt.Tooltip("holiday_count:Q", title="Holidays"),
                alt.Tooltip("holiday_dates_display:N", title="Holiday dates"),
            ],
        )
        .properties(height=180)
    )
    if holidays:
        holiday_df = pd.DataFrame(
            [{"date": holiday.start, "label": holiday.label} for holiday in holidays]
        )
        min_date = df["start"].min()
        max_date = df["end_inclusive"].max()
        holiday_df = holiday_df[
            (holiday_df["date"] >= min_date) & (holiday_df["date"] <= max_date)
        ]
        block_ranges = df[["label", "start", "end_inclusive"]]

        def coverage_for(date_value: date) -> str:
            matches = block_ranges[
                (block_ranges["start"] <= date_value)
                & (block_ranges["end_inclusive"] >= date_value)
            ]["label"].tolist()
            return ", ".join(matches) if matches else "None"

        holiday_df["covered_blocks"] = holiday_df["date"].apply(coverage_for)

        holiday_layer = (
            alt.Chart(holiday_df)
            .mark_rule(color="#f4d35e", strokeWidth=1, strokeDash=[4, 2], opacity=0.35)
            .encode(
                x=alt.X("date:T"),
                tooltip=[
                    alt.Tooltip("label:N", title="Holiday"),
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip("covered_blocks:N", title="Within blocks"),
                ],
            )
        )
        chart = alt.layer(holiday_layer, base_chart)
    else:
        chart = base_chart

    st.altair_chart(chart, use_container_width=True)
    table_df = df[
        [
            "label",
            "start",
            "end_inclusive",
            "weeks",
            "days",
            "holiday_count",
            "holiday_dates_display",
        ]
    ].rename(
        columns={
            "end_inclusive": "end",
            "holiday_count": "holidays",
            "holiday_dates_display": "holiday dates",
        }
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

    saved_a_name = (saved_plan or {}).get("caregiver_a_name", "Caregiver 1")
    saved_b_name = (saved_plan or {}).get("caregiver_b_name", "Caregiver 2")
    caregiver_a_input = st.text_input("Caregiver 1 name", value=saved_a_name)
    caregiver_b_input = st.text_input("Caregiver 2 name", value=saved_b_name)
    caregiver_a_name = (
        caregiver_a_input.strip() or "Caregiver 1"
    )
    caregiver_b_name = (
        caregiver_b_input.strip() or "Caregiver 2"
    )
    stored_holidays = saved_plan.get("holidays", []) if saved_plan else []
    holiday_file = st.file_uploader(
        "Import bank holidays (.ics)", type="ics", accept_multiple_files=False
    )
    uploaded_holidays = parse_bank_holidays(holiday_file)
    if holiday_file:
        holidays = uploaded_holidays
    else:
        holidays = stored_holidays

    holiday_lookup_map = holiday_lookup(holidays)
    if holiday_file:
        if not uploaded_holidays:
            st.warning("No valid events found in the provided calendar.")
        else:
            st.success(f"Imported {len(uploaded_holidays)} bank holiday events.")
    elif holidays:
        st.info(f"Loaded {len(holidays)} stored bank holiday events.")
    st.divider()

    caregiver_a_intervals = collect_interval_inputs(
        f"{caregiver_a_name} plan",
        "caregiver-a",
        birth_date,
        saved_plan["caregiver-a"] if saved_plan else None,
    )
    st.divider()
    caregiver_b_intervals = collect_interval_inputs(
        f"{caregiver_b_name} plan",
        "caregiver-b",
        birth_date,
        saved_plan["caregiver-b"] if saved_plan else None,
    )

    caregiver_a_records = build_records(caregiver_a_name, caregiver_a_intervals)
    caregiver_b_records = build_records(caregiver_b_name, caregiver_b_intervals)
    overlap_records = build_overlap_records(caregiver_a_records, caregiver_b_records)
    all_records = caregiver_a_records + caregiver_b_records + overlap_records

    st.divider()
    render_chart(all_records, holidays, holiday_lookup_map)
    if st.button("Save plan for next time"):
        save_plan(
            birth_date,
            caregiver_a_intervals,
            caregiver_b_intervals,
            caregiver_a_name,
            caregiver_b_name,
            holidays,
        )
        st.success("Plan saved locally (.streamlit/last_plan.json).")


if __name__ == "__main__":
    main()
