#!/usr/bin/env python3
"""
Meridian SMTP Server
Listens on port 2525 for forwarded newsletter emails.
Parses and inserts into the newsletters table in meridian.db.
"""

import asyncio
import email
import email.policy
import email.utils
import hashlib
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from aiosmtpd.controller import Controller

BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "meridian.db"
LOG_PATH = BASE_DIR / "logs" / "smtp.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
)
log = logging.getLogger("meridian_smtp")

SOURCE_MAP = {
    "substack.com":    "Substack",
    "beehiiv.com":     "Beehiiv",
    "convertkit.com":  "ConvertKit",
    "mailchimp.com":   "Mailchimp",
}

def detect_source(from_addr):
    from_addr = from_addr.lower()
    for domain, name in SOURCE_MAP.items():
        if domain in from_addr:
            return name
    if "@" in from_addr:
        return from_addr.split("@")[-1].strip(">")
    return "Unknown"

def insert_newsletter(message_id, source, subject, body_html, body_text, received_at):
    try:
        with sqlite3.connect(DB_PATH) as cx:
            cx.execute("""
                INSERT OR IGNORE INTO newsletters
                    (gmail_id, source, subject, body_html, body_text, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, source, subject, body_html, body_text, received_at))
            cx.commit()
        log.info(f"Inserted: '{subject[:60]}' from {source}")
    except Exception as e:
        log.error(f"DB error: {e}")

class MeridianHandler:
    async def handle_DATA(self, server, session, envelope):
        try:
            raw = envelope.content
            if isinstance(raw, str):
                raw = raw.encode("utf-8", errors="replace")
            msg = email.message_from_bytes(raw, policy=email.policy.default)
            message_id = msg.get("Message-ID") or hashlib.md5(raw[:200]).hexdigest()
            subject    = msg.get("Subject", "(no subject)")
            from_addr  = msg.get("From", "")
            date_str   = msg.get("Date", "")
            source     = detect_source(from_addr)
            try:
                received_at = email.utils.parsedate_to_datetime(date_str).isoformat()
            except Exception:
                received_at = datetime.now().isoformat()
            body_html = body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/html" and not body_html:
                        body_html = part.get_content()
                    elif ct == "text/plain" and not body_text:
                        body_text = part.get_content()
            else:
                ct = msg.get_content_type()
                if ct == "text/html":
                    body_html = msg.get_content()
                else:
                    body_text = msg.get_content()
            log.info(f"Received: '{subject[:60]}' from {from_addr}")
            insert_newsletter(message_id, source, subject, body_html, body_text, received_at)
        except Exception as e:
            log.error(f"Handler error: {e}", exc_info=True)
        return "250 Message accepted"

if __name__ == "__main__":
    handler    = MeridianHandler()
    controller = Controller(handler, hostname="127.0.0.1", port=2525)
    controller.start()
    log.info("Meridian SMTP server started on 127.0.0.1:2525")
    print("Meridian SMTP server running on 127.0.0.1:2525 — Ctrl+C to stop")
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        controller.stop()
        log.info("Meridian SMTP server stopped")
