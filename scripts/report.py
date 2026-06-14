#!/usr/bin/env python3
"""Generate a Todoist completed-task report for a chosen time period.

Usage (from project root):
    python scripts/report.py --period today
    python scripts/report.py --period yesterday
    python scripts/report.py --period last-week
    python scripts/report.py --from 01-05-2026 --to 31-05-2026
    python scripts/report.py -p yesterday
"""
import argparse
import sys

import _bootstrap  # noqa: F401  # adds project root to sys.path

from todoist_reports import (
    DATE_FORMAT_HELP,
    PERIODS,
    run_custom_range_report,
    run_period_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown report of completed Todoist tasks.",
    )
    parser.add_argument(
        "-p",
        "--period",
        choices=PERIODS,
        help="time period to report on (today, yesterday, or last-week)",
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        metavar="DATE",
        help=f"custom range start date ({DATE_FORMAT_HELP})",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        metavar="DATE",
        help=f"custom range end date ({DATE_FORMAT_HELP})",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    using_period = args.period is not None
    using_from = args.from_date is not None
    using_to = args.to_date is not None

    if using_period and (using_from or using_to):
        parser.error("use either --period or both --from and --to, not both")

    if using_from or using_to:
        if not (using_from and using_to):
            parser.error("both --from and --to are required for a custom date range")
        run_custom_range_report(args.from_date, args.to_date)
        return

    if using_period:
        run_period_report(args.period)
        return

    parser.error("provide either --period or both --from and --to")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
