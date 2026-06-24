#!/usr/bin/env python3
"""Test SMTP login without generating a Todoist report.

Usage (from project root):
    python scripts/test_smtp.py
"""
import sys

import smtplib

import _bootstrap  # noqa: F401

from todoist_reports.email import get_email_config


def main() -> None:
    config = get_email_config()
    host = config["smtp_host"]
    port = config["smtp_port"]
    user = config["smtp_user"]
    use_ssl = config["smtp_use_ssl"]
    use_tls = config["smtp_use_tls"]

    print("SMTP configuration:")
    print(f"  host: {host}")
    print(f"  port: {port}")
    print(f"  user: {user}")
    print(f"  ssl:  {use_ssl}")
    print(f"  tls:  {use_tls}")
    print()

    password = config["smtp_password"]
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
            server.ehlo()
        else:
            server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()

        server.login(user, password)  # type: ignore[arg-type]
        server.quit()
        print("SMTP login successful.")
    except smtplib.SMTPAuthenticationError as exc:
        print(f"SMTP authentication failed: {exc}", file=sys.stderr)
        print(
            "\nFor Hostinger Email (MX: mx1.hostinger.com): use "
            "SMTP_HOST=smtp.hostinger.com, full email as SMTP_USER, and verify "
            "the password in hPanel → Emails → Manage (try resetting it).\n"
            "If port 465 fails, switch to port 587 with SMTP_USE_TLS=true.",
            file=sys.stderr,
        )
        sys.exit(1)
    except smtplib.SMTPException as exc:
        print(f"SMTP error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
