#!/usr/bin/env python3
"""Generate a Todoist report and email it as a Markdown attachment.

Usage (from project root):
    python scripts/report_email.py --period last-week
    python scripts/report_email.py --period yesterday
    python scripts/report_email.py --from 01-05-2026 --to 31-05-2026
"""
import argparse
import sys

import smtplib

import _bootstrap  # noqa: F401  # adds project root to sys.path

from todoist_reports import (
    DATE_FORMAT_HELP,
    PERIODS,
    generate_report,
    get_timezone,
    parse_display_date,
    resolve_custom_range,
    resolve_period,
    send_report_email,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a Todoist report and email it as an attachment.",
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


def run_and_email_period(period: str) -> list[str]:
    tz = get_timezone()
    title, since, until, filename = resolve_period(period, tz)
    report_path = generate_report(title, since, until, filename)
    return send_report_email(report_path, subject=title)


def run_and_email_custom_range(from_date: str, to_date: str) -> list[str]:
    tz = get_timezone()
    title, since, until, filename = resolve_custom_range(
        parse_display_date(from_date),
        parse_display_date(to_date),
        tz,
    )
    report_path = generate_report(title, since, until, filename)
    return send_report_email(report_path, subject=title)


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
        recipients = run_and_email_custom_range(args.from_date, args.to_date)
    elif using_period:
        recipients = run_and_email_period(args.period)
    else:
        parser.error("provide either --period or both --from and --to")
        return

    print(f"Report emailed to: {', '.join(recipients)}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except smtplib.SMTPException as exc:
        print(f"Error: email delivery failed: {exc}", file=sys.stderr)
        sys.exit(1)
