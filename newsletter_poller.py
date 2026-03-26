import os
import sqlite3
import base64
import re
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_PATH = '/Users/alexdakers/meridian-server/token.json'
CREDS_PATH = '/Users/alexdakers/meridian-server/credentials.json'
DB_PATH = '/Users/alexdakers/meridian-server/meridian.db'

SENDERS = {
    'bloomberg': 'bloomberg',
    'financial times': 'ft',
    'ft.com': 'ft',
    'economist': 'economist',
    'morganstanley': 'morgan_stanley',
    'goldmansachs': 'goldman_sachs',
    'goldman sachs': 'goldman_sachs',
}

def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def detect_source(from_addr, subject):
    combined = (from_addr + ' ' + subject).lower()
    for keyword, source in SENDERS.items():
        if keyword in combined:
            return source
    return 'other'

def get_body(payload):
    html, text = '', ''
    def walk(part):
        nonlocal html, text
        mime = part.get('mimeType', '')
        body = part.get('body', {})
        data = body.get('data', '')
        if data:
            decoded = base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
            if mime == 'text/html' and not html:
                html = decoded
            elif mime == 'text/plain' and not text:
                text = decoded
        for sub in part.get('parts', []):
            walk(sub)
    walk(payload)
    return html, text

def poll():
    service = get_service()
    db = sqlite3.connect(DB_PATH)
    c = db.cursor()

    query = ' OR '.join([
        'from:bloomberg', 'from:ft.com', 'from:economist.com',
        'from:morganstanley.com', 'from:goldmansachs.com'
    ])

    results = service.users().messages().list(
        userId='me', q=query, maxResults=50
    ).execute()

    messages = results.get('messages', [])
    new_count = 0

    for msg in messages:
        msg_id = msg['id']
        existing = c.execute('SELECT id FROM newsletters WHERE gmail_id=?', (msg_id,)).fetchone()
        if existing:
            continue

        full = service.users().messages().get(
            userId='me', id=msg_id, format='full'
        ).execute()

        headers = {h['name'].lower(): h['value'] for h in full['payload']['headers']}
        subject = headers.get('subject', '(no subject)')
        from_addr = headers.get('from', '')
        date_str = headers.get('date', '')

        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str).isoformat()
        except:
            received_at = datetime.utcnow().isoformat()

        source = detect_source(from_addr, subject)
        html, text = get_body(full['payload'])

        c.execute('''
            INSERT OR IGNORE INTO newsletters
            (gmail_id, source, subject, body_html, body_text, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (msg_id, source, subject, html, text, received_at))
        new_count += 1

    db.commit()
    db.close()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Polled — {new_count} new newsletters saved.")

if __name__ == '__main__':
    poll()
