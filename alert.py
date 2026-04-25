#!/usr/bin/env python3
"""
Meridian Tier-3 alert helper.

Usage (CLI):
    alert.py "<subject>" "<body>" [--severity tier3]
    echo "body" | alert.py "<subject>"

Usage (importable):
    from alert import send_alert
    send_alert("subject", "body", severity="tier3")

Reads ICLOUD_EMAIL + ICLOUD_APP_PASSWORD from /etc/meridian/secrets.env
(or current process env if already set). Sends via smtp.mail.me.com:587.
Both From and To are the same iCloud address — Meridian alerts to self.

Exits 0 on success, non-zero on failure. Failure prints to stderr.
This is the Phase-2 alerting skeleton (PHASE_2_PLAN § 6 / P2-1).
Channel upgrades (Pushover, APNs, etc) are explicitly Phase 4.
"""
import os
import sys
import smtplib
import socket
import argparse
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from datetime import datetime, timezone

SECRETS_FILE = "/etc/meridian/secrets.env"
SMTP_HOST = "smtp.mail.me.com"
SMTP_PORT = 587


def _load_secrets_env():
    """Populate os.environ from secrets file if not already set."""
    if "ICLOUD_EMAIL" in os.environ and "ICLOUD_APP_PASSWORD" in os.environ:
        return
    if not os.path.exists(SECRETS_FILE):
        return
    with open(SECRETS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def send_alert(subject, body, severity="tier3"):
    """
    Send a Meridian alert email.

    Returns True on success, raises on failure (so callers see the traceback
    in cron logs). For CLI use, the wrapper turns exceptions into exit codes.
    """
    _load_secrets_env()
    sender = os.environ.get("ICLOUD_EMAIL")
    password = os.environ.get("ICLOUD_APP_PASSWORD")
    if not sender or not password:
        raise RuntimeError(
            "ICLOUD_EMAIL / ICLOUD_APP_PASSWORD not set; "
            "check /etc/meridian/secrets.env"
        )

    hostname = socket.gethostname()
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    severity_tag = severity.upper()

    full_subject = f"[Meridian {severity_tag}] {subject}"
    full_body = (
        f"Severity: {severity_tag}\n"
        f"Host: {hostname}\n"
        f"Time: {timestamp}\n"
        f"---\n"
        f"{body}\n"
    )

    msg = MIMEText(full_body, _charset="utf-8")
    msg["Subject"] = full_subject
    msg["From"] = sender
    msg["To"] = sender
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain="meridianreader.com")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(sender, password)
        smtp.sendmail(sender, [sender], msg.as_string())

    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Meridian Tier-3 alert helper")
    parser.add_argument("subject", help="Alert subject line")
    parser.add_argument(
        "body",
        nargs="?",
        default=None,
        help="Alert body. If omitted, read from stdin.",
    )
    parser.add_argument(
        "--severity",
        default="tier3",
        choices=["tier1", "tier2", "tier3", "info"],
        help="Severity tag (default: tier3)",
    )
    args = parser.parse_args(argv)

    body = args.body
    if body is None:
        body = sys.stdin.read().strip() or "(no body)"

    try:
        send_alert(args.subject, body, severity=args.severity)
    except Exception as e:
        print(f"alert.py: send failed: {e}", file=sys.stderr)
        return 2

    print(f"alert.py: sent ({args.severity}) to iCloud", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
