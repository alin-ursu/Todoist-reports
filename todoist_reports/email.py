"""Send generated reports via SMTP."""
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from todoist_reports.client import PROJECT_ROOT


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_recipients(value: str) -> list[str]:
    return [address.strip() for address in value.split(",") if address.strip()]


def get_email_config() -> dict[str, str | int | bool | list[str]]:
    """Load and validate SMTP settings from .env."""
    load_dotenv(PROJECT_ROOT / ".env")

    missing = [
        name
        for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO")
        if not (os.getenv(name) or "").strip()
    ]
    if missing:
        raise ValueError(
            "Missing email configuration. Set in .env: "
            + ", ".join(missing)
        )

    email_to = _parse_recipients(os.environ["EMAIL_TO"])
    if not email_to:
        raise ValueError("EMAIL_TO must contain at least one recipient address.")

    smtp_user = os.environ["SMTP_USER"].strip()
    email_from = (os.getenv("EMAIL_FROM") or smtp_user).strip()

    return {
        "smtp_host": os.environ["SMTP_HOST"].strip(),
        "smtp_port": int((os.getenv("SMTP_PORT") or "587").strip()),
        "smtp_user": smtp_user,
        "smtp_password": os.environ["SMTP_PASSWORD"].strip(),
        "email_from": email_from,
        "email_to": email_to,
        "smtp_use_tls": _env_bool("SMTP_USE_TLS", True),
        "smtp_use_ssl": _env_bool("SMTP_USE_SSL", False),
    }


def send_report_email(
    report_path: Path,
    subject: str,
    body: str | None = None,
) -> list[str]:
    """Email a Markdown report as an attachment. Returns recipient addresses."""
    report_path = Path(report_path)
    if not report_path.is_file():
        raise ValueError(f"Report file not found: {report_path}")

    config = get_email_config()
    recipients: list[str] = config["email_to"]  # type: ignore[assignment]

    if body is None:
        body = (
            f"Your Todoist report is attached ({report_path.name}).\n"
            f"Saved copy: {report_path}"
        )

    message = MIMEMultipart()
    message["From"] = config["email_from"]  # type: ignore[assignment]
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    attachment = MIMEBase("text", "markdown")
    attachment.set_payload(report_path.read_bytes())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=report_path.name,
    )
    message.attach(attachment)

    smtp_host = config["smtp_host"]  # type: ignore[assignment]
    smtp_port = config["smtp_port"]  # type: ignore[assignment]

    if config["smtp_use_ssl"]:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            _login_and_send(server, config, recipients, message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            if config["smtp_use_tls"]:
                server.starttls()
                server.ehlo()
            _login_and_send(server, config, recipients, message)

    return recipients


def _login_and_send(
    server: smtplib.SMTP,
    config: dict[str, str | int | bool | list[str]],
    recipients: list[str],
    message: MIMEMultipart,
) -> None:
    smtp_user = config["smtp_user"]  # type: ignore[assignment]
    smtp_password = config["smtp_password"]  # type: ignore[assignment]
    smtp_port = config["smtp_port"]  # type: ignore[assignment]

    try:
        server.login(smtp_user, smtp_password)
    except smtplib.SMTPAuthenticationError as exc:
        mode = "SSL" if config["smtp_use_ssl"] else "STARTTLS" if config["smtp_use_tls"] else "plain"
        raise ValueError(
            f"SMTP authentication failed for {smtp_user} on port {smtp_port} ({mode}). "
            "Check SMTP_USER (full email address) and SMTP_PASSWORD — reset the mailbox "
            "password in Hostinger hPanel → Emails → Manage if unsure. "
            "Hostinger Email uses SMTP_HOST=smtp.hostinger.com; Titan Mail uses "
            "smtp.titan.email (check your domain MX records). "
            "Ensure only one SMTP_PORT / SMTP_USE_SSL / SMTP_USE_TLS block is active in .env."
        ) from exc

    server.sendmail(config["email_from"], recipients, message.as_string())  # type: ignore[arg-type]
