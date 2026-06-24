#!/usr/bin/env python3
"""Generate a report of tasks completed during the previous calendar week.

"Last week" is the 7-day block before the current week, based on WEEK_START_DAY
in .env (default: monday).

Usage (from project root):
    python scripts/report.py --period last-week
    python scripts/report_last_week.py
"""
import _bootstrap  # noqa: F401  # adds project root to sys.path

from todoist_reports import run_period_report


def main() -> None:
    run_period_report("last-week")


if __name__ == "__main__":
    main()
