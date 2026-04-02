import sqlite3, json, time
from datetime import datetime
import subprocess

results = {}

# Check FA profile cookies via Chromium sqlite DB
import os
fa_cookies_db = '/Users/alexdakers/meridian-server/fa_profile/Default/Cookies'
if os.path.exists(fa_cookies_db):
    subprocess.run(['cp', fa_cookies_db, '/tmp/fa_cookies_copy.db'], check=True)
    c = sqlite3.connect('/tmp/fa_cookies_copy.db')
    rows = c.execute(
        "SELECT host_key, name, expires_utc, last_access_utc, is_secure, is_httponly "
        "FROM cookies WHERE host_key LIKE '%foreignaffairs%' ORDER BY last_access_utc DESC"
    ).fetchall()
    now_chrome = int((time.time() + 11644473600) * 1e6)
    cookies = []
    for host, name, expires, last_access, secure, httponly in rows:
        exp_ts = (expires / 1e6) - 11644473600 if expires > 0 else 0
        acc_ts = (last_access / 1e6) - 11644473600 if last_access > 0 else 0
        expired = expires > 0 and expires < now_chrome
        cookies.append({
            'name': name,
            'expires': datetime.fromtimestamp(exp_ts).strftime('%Y-%m-%d') if exp_ts > 0 else 'session',
            'last_access': datetime.fromtimestamp(acc_ts).strftime('%Y-%m-%d %H:%M') if acc_ts > 0 else 'never',
            'expired': expired,
            'secure': bool(secure)
        })
    results['fa_cookies'] = cookies
    results['total_fa_cookies'] = len(cookies)
    results['expired_count'] = sum(1 for c in cookies if c['expired'])
    results['valid_count'] = sum(1 for c in cookies if not c['expired'])
    # Key auth cookies to look for
    auth_names = ['laravel_session', 'remember_web', 'XSRF-TOKEN', 'fa_session', '__stripe_mid', 'wordpress_logged_in', 'auth_token']
    results['auth_cookies'] = [c for c in cookies if any(a in c['name'] for a in auth_names)]
else:
    results['error'] = 'fa_profile/Default/Cookies not found'

with open('/Users/alexdakers/meridian-server/tmp_diag.txt', 'w') as f:
    f.write(json.dumps(results, indent=2))
print("DONE")
