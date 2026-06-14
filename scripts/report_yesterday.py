#!/usr/bin/env python3
"""Generate a report of tasks completed yesterday.

Usage (from project root):
    python scripts/report.py --period yesterday
    python scripts/report_yesterday.py
"""
import _bootstrap  # noqa: F401  # adds project root to sys.path

from todoist_reports import run_period_report


def main() -> None:
    run_period_report("yesterday")


if __name__ == "__main__":
    main()
