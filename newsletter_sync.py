#!/usr/bin/env python3
"""
newsletter_sync.py — polls iCloud IMAP for Bloomberg newsletters
and stores them in the Meridian newsletters DB table.
"""
import imaplib, email, sqlite3, hashlib, logging
from email.header import decode_header
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup
from pathlib import Path

log = logging.getLogger(__name__)

DB_PATH  = Path(__file__).parent / "meridian.db"
IMAP_HOST = "imap.mail.me.com"
IMAP_PORT = 993
USERNAME  = "alex.dakers@icloud.com"
PASSWORD  = "iwjx-qkgo-ntat-yunw"

# Senders → newsletter name mapping
SENDERS = {
    "noreply@news.bloomberg.com": "Points of Return",
    "bloomberg@mail.bloomberg.com": "Bloomberg Markets Daily",
}

def decode_str(s):
    if s is None: return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)

def extract_body(msg):
    """Extract HTML and plain text body from email message."""
    body_html, body_text = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd: continue
            payload = part.get_payload(decode=True)
            if payload is None: continue
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if ct == "text/html" and not body_html:
                body_html = decoded
            elif ct == "text/plain" and not body_text:
                body_text = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body_text = payload.decode(charset, errors="replace")
    # Extract plain text from HTML if no plain text
    if body_html and not body_text:
        soup = BeautifulSoup(body_html, "html.parser")
        body_text = soup.get_text(separator=" ", strip=True)
    return body_html, body_text

def sync_newsletters():
    """Poll iCloud IMAP and store new Bloomberg newsletters."""
    added = 0
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(USERNAME, PASSWORD)
        mail.select("INBOX")

        # Search for emails sent to the newsletters alias
        # Catches both direct delivery and manual forwards
        all_ids = set()
        searches = [
            '(TO "meridian.newsletters@icloud.com")',
            '(TO "meridian.newsletters")',
        ]
        for search in searches:
            _, data = mail.search(None, search)
            if data[0]:
                for mid in data[0].split():
                    all_ids.add(mid)
        # Also search by known Bloomberg senders (for direct delivery)
        for sender in SENDERS:
            _, data = mail.search(None, f'(FROM "{sender}")')
            if data[0]:
                for mid in data[0].split():
                    all_ids.add(mid)

        log.info(f"Newsletter sync: found {len(all_ids)} Bloomberg emails in iCloud")

        conn = sqlite3.connect(DB_PATH)
        for mid in all_ids:
            _, data = mail.fetch(mid, "(BODY[])")
            raw = None
            for part in data:
                if isinstance(part, tuple) and len(part) > 1:
                    raw = part[1]
                    break
            if not raw or not isinstance(raw, bytes):
                continue
            msg = email.message_from_bytes(raw)

            # Use Message-ID as dedup key
            msg_id = msg.get("Message-ID", "").strip()
            if not msg_id:
                msg_id = hashlib.md5(raw[:200]).hexdigest()

            # Skip if already stored
            exists = conn.execute(
                "SELECT 1 FROM newsletters WHERE gmail_id=?", (msg_id,)
            ).fetchone()
            if exists: continue

            # Skip Gmail system emails
            subject_raw = decode_str(msg.get("Subject", ""))
            from_raw = msg.get("From", "")
            if any(skip in subject_raw for skip in [
                "Gmail Forwarding confirmation",
                "Forwarding confirmation",
            ]) or "forwarding-noreply@google.com" in from_raw:
                log.info(f"Newsletter: skipping system email '{subject_raw[:50]}'")
                continue

            # Parse fields
            from_addr = msg.get("From", "")
            subject_check = decode_str(msg.get("Subject", "")).lower()
            source = "Bloomberg"
            for sender, name in SENDERS.items():
                if sender in from_addr:
                    source = name
                    break
            # Fallback: detect from subject for forwarded emails
            if source == "Bloomberg":
                if "points of return" in subject_check:
                    source = "Points of Return"
                elif "markets daily" in subject_check:
                    source = "Bloomberg Markets Daily"
                elif "london rush" in subject_check:
                    source = "Bloomberg London Rush"

            subject = decode_str(msg.get("Subject", ""))
            try:
                received_at = parsedate_to_datetime(msg.get("Date", "")).isoformat()
            except:
                from datetime import datetime
                received_at = datetime.now().isoformat()

            body_html, body_text = extract_body(msg)

            conn.execute("""
                INSERT INTO newsletters (gmail_id, source, subject, body_html, body_text, received_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (msg_id, source, subject, body_html, body_text, received_at))
            conn.commit()
            added += 1
            log.info(f"Newsletter: stored '{subject[:60]}' ({source})")

        conn.close()
        mail.logout()
        log.info(f"Newsletter sync complete — {added} new newsletters added")
    except Exception as e:
        log.error(f"Newsletter sync error: {e}", exc_info=True)
    return added

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sync_newsletters()
