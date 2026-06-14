"""Map report period names to date ranges and output filenames."""
from datetime import date, datetime, timedelta, tzinfo
from pathlib import Path

from todoist_reports.client import (
    DISPLAY_DATE_FORMAT,
    DISPLAY_DATE_FORMAT_HELP,
    day_bounds,
    format_display_date,
    generate_report,
    get_timezone,
    last_week_bounds,
)

DATE_FORMAT = DISPLAY_DATE_FORMAT
DATE_FORMAT_HELP = DISPLAY_DATE_FORMAT_HELP
PERIODS = ("today", "yesterday", "last-week")


def parse_display_date(value: str) -> date:
    """Parse a date string in dd-mm-yyyy format."""
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError(
            f"Invalid date {value!r}. Use {DATE_FORMAT_HELP} format, e.g. 06-06-2026."
        ) from exc


def resolve_period(
    period: str,
    tz: tzinfo,
    today: date | None = None,
) -> tuple[str, datetime, datetime, str]:
    """Return (title, since, until, filename) for a named report period."""
    if period not in PERIODS:
        raise ValueError(
            f"Unknown period {period!r}. Choose from: {', '.join(PERIODS)}"
        )

    reference_day = today or date.today()

    if period == "today":
        since, until = day_bounds(reference_day, tz)
        day_label = format_display_date(reference_day)
        return (
            f"Todoist Report: today ({day_label})",
            since,
            until,
            f"today_{day_label}.md",
        )

    if period == "yesterday":
        target_day = reference_day - timedelta(days=1)
        since, until = day_bounds(target_day, tz)
        day_label = format_display_date(target_day)
        return (
            f"Todoist Report: Yesterday ({day_label})",
            since,
            until,
            f"yesterday_{day_label}.md",
        )

    since, until, week_start, week_end = last_week_bounds(reference_day, tz)
    week_start_label = format_display_date(week_start)
    week_end_label = format_display_date(week_end)
    return (
        f"Todoist Report: Last Week ({week_start_label} to {week_end_label})",
        since,
        until,
        f"last_week_{week_start_label}_to_{week_end_label}.md",
    )


def resolve_custom_range(
    from_date: date,
    to_date: date,
    tz: tzinfo,
) -> tuple[str, datetime, datetime, str]:
    """Return (title, since, until, filename) for a custom inclusive date range."""
    if from_date > to_date:
        raise ValueError(
            f"Start date {format_display_date(from_date)} must be on or before "
            f"end date {format_display_date(to_date)}."
        )

    since, _ = day_bounds(from_date, tz)
    _, until = day_bounds(to_date, tz)
    from_label = format_display_date(from_date)
    to_label = format_display_date(to_date)
    return (
        f"Todoist Report: {from_label} to {to_label}",
        since,
        until,
        f"custom_{from_label}_to_{to_label}.md",
    )


def run_period_report(period: str) -> Path:
    """Generate and save a report for the given period name."""
    tz = get_timezone()
    title, since, until, filename = resolve_period(period, tz)
    return generate_report(title, since, until, filename)


def run_custom_range_report(from_date: str, to_date: str) -> Path:
    """Generate and save a report for a custom dd-mm-yyyy date range."""
    tz = get_timezone()
    title, since, until, filename = resolve_custom_range(
        parse_display_date(from_date),
        parse_display_date(to_date),
        tz,
    )
    return generate_report(title, since, until, filename)
