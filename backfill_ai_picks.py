"""
Non-interactive backfill — runs scoring, saves results to logs/backfill_preview.txt
then automatically saves to DB.
"""
import json, sqlite3, urllib.request, subprocess, tempfile, os, sys, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path("/Users/alexdakers/meridian-server")
DB_PATH = str(BASE_DIR / "meridian.db")

def load_creds():
    return json.load(open(BASE_DIR / "credentials.json"))

def make_id(source, url):
    import hashlib
    return hashlib.md5(f"{source}:{url}".encode()).hexdigest()[:16]

def now_ts():
    return int(datetime.now().timestamp() * 1000)

log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

# ── 1. Known URLs ──────────────────────────────────────────────────────────
with sqlite3.connect(DB_PATH) as cx:
    known_articles = set(r[0] for r in cx.execute("SELECT url FROM articles WHERE url!=''").fetchall())
    known_suggested = set(r[0] for r in cx.execute("SELECT url FROM suggested_articles WHERE url!=''").fetchall())
known = known_articles | known_suggested
log(f"Known: {len(known_articles)} articles, {len(known_suggested)} suggested")

# ── 2. Taste profile ───────────────────────────────────────────────────────
with sqlite3.connect(DB_PATH) as cx:
    ft_row = cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_followed_topics'").fetchone()
    tt_row = cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'").fetchone()
followed_topics = json.loads(ft_row[0]) if ft_row else []
taste_titles = json.loads(tt_row[0]) if tt_row else []
topics_str = ", ".join(followed_topics)
taste_str = "\n".join(f"- {t}" for t in taste_titles[:50])
log(f"Taste: {len(followed_topics)} topics, {len(taste_titles)} saves")

# ── 3. Scrape FT feed ──────────────────────────────────────────────────────
log("Scraping FT feed timeline...")
ft_script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
ft_out_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
ft_script_path = ft_script_file.name
ft_out_path = ft_out_file.name

ft_script_file.write("""
import sys, json
from playwright.sync_api import sync_playwright

profile_dir = sys.argv[1]
out_path = sys.argv[2]

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        profile_dir, headless=False,
        args=["--window-position=-3000,-3000","--window-size=1280,900",
              "--disable-blink-features=AutomationControlled","--no-sandbox"]
    )
    page = browser.new_page()
    page.goto("https://www.ft.com/myft/following/197493b5-7e8e-4f13-8463-3c046200835c/time",
              wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(5000)
    articles = page.evaluate('''() => {
        if (window._feedTimelineTeasers) {
            return window._feedTimelineTeasers.map(a => ({
                title: a.title || a.headline || "",
                url: "https://www.ft.com" + (a.url || a.relativeUrl || ""),
                pub_date: a.publishedDate ? a.publishedDate.slice(0,10) : "",
                standfirst: a.standfirst || a.summary || "",
                is_podcast: a.indicators ? a.indicators.isPodcast : false,
            }));
        }
        const results = []; const seen = new Set();
        document.querySelectorAll('a[href*="/content/"]').forEach(a => {
            const url = a.href.split("?")[0];
            const title = a.innerText.trim();
            if (title.length > 15 && url.includes("ft.com/content/") && !seen.has(url)) {
                seen.add(url);
                results.push({title, url, pub_date: "", standfirst: "", is_podcast: false});
            }
        });
        return results;
    }''')
    browser.close()

with open(out_path, 'w') as f:
    json.dump(articles, f)
""")
ft_script_file.close()
ft_out_file.close()

proc = subprocess.run(
    ["python3", ft_script_path, str(BASE_DIR / "ft_profile"), ft_out_path],
    timeout=90, capture_output=True
)
if proc.returncode != 0:
    log(f"FT scrape failed: {proc.stderr.decode()[:300]}")
    sys.exit(1)

with open(ft_out_path) as f:
    ft_articles = json.load(f)
os.unlink(ft_script_path)
os.unlink(ft_out_path)
log(f"FT feed: {len(ft_articles)} articles")

# ── 4. Filter: last 14 days, unsaved ──────────────────────────────────────
cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
candidates = [
    a for a in ft_articles
    if not a.get('is_podcast')
    and a['url'] not in known
    and '/content/' in a['url']
    and (not a.get('pub_date') or a.get('pub_date','') >= cutoff)
]
candidates.sort(key=lambda a: a.get('pub_date',''), reverse=True)
log(f"Candidates (last 14d, unsaved): {len(candidates)}")
if candidates:
    log(f"Date range: {candidates[-1].get('pub_date','?')} to {candidates[0].get('pub_date','?')}")

if not candidates:
    log("No candidates to score.")
    sys.exit(0)

# ── 5. Score in batches of 50 ─────────────────────────────────────────────
api_key = load_creds().get("anthropic_api_key","")
all_scored = []

for batch_start in range(0, len(candidates), 50):
    batch = candidates[batch_start:batch_start+50]
    log(f"Scoring batch {batch_start//50 + 1}/{(len(candidates)-1)//50 + 1} ({len(batch)} articles)...")

    articles_list = json.dumps([
        {"title": a["title"], "url": a["url"], "source": "Financial Times",
         "standfirst": a.get("standfirst","")} for a in batch
    ])
    prompt = (
        f"You are scoring news articles for a senior intelligence analyst.\n"
        f"FOLLOWED TOPICS: {topics_str}.\n\n"
        + (f"RECENT SAVES (calibrate taste):\n{taste_str}\n\n" if taste_str else "")
        + "Score 0-10:\n"
        "9-10: Concrete breaking event (war, sanctions, central bank, market shock)\n"
        "7-8: High-quality analysis (markets, geopolitics, economic policy, AI with real impact)\n"
        "6: Relevant essays/analysis on followed topics\n"
        "0-5: Not relevant\n"
        "Respond ONLY with JSON array same order as input:\n"
        '[{"score":7,"reason":"one sentence"}]'
        f"\n\nArticles:\n{articles_list}"
    )
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 6000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log(f"  Sonnet failed: {e}")
        continue

    text = "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text").strip()
    if "```" in text:
        text = text.split("```",2)[1]
        if text.startswith("json"): text = text[4:]
        text = text.rsplit("```",1)[0].strip()
    m = re.search(r'\[[\s\S]*\]', text)
    scores = json.loads(m.group(0)) if m else []
    log(f"  Got {len(scores)} scores")
    all_scored.extend(list(zip(batch, scores)))

# ── 6. Results ─────────────────────────────────────────────────────────────
log(f"\n{'='*60}")
log(f"SCORED: {len(all_scored)} articles")
log(f"{'='*60}")

feed_arts = []
sug_arts = []
for art, s in all_scored:
    score = s.get("score",0)
    reason = s.get("reason","")
    marker = " ← FEED" if score >= 8 else (" ← suggested" if score >= 6 else "")
    log(f"  [{score}] {art['title'][:70]}{marker}")
    if score >= 8:
        feed_arts.append((art, score, reason))
    elif score >= 6:
        sug_arts.append((art, score, reason))

log(f"\nFeed (>=8): {len(feed_arts)}")
log(f"Suggested (6-7): {len(sug_arts)}")

# Save preview
with open(BASE_DIR / "logs" / "backfill_preview.txt", "w") as f:
    f.write("\n".join(log_lines))
log(f"\nPreview saved to logs/backfill_preview.txt")

# ── 7. Save to DB ──────────────────────────────────────────────────────────
with sqlite3.connect(DB_PATH) as cx:
    feed_saved = sug_saved = 0
    for art, score, reason in feed_arts:
        art_id = make_id("Financial Times", art["url"])
        cx.execute(
            'INSERT OR IGNORE INTO articles '
            '(id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (art_id,"Financial Times",art["url"],art["title"],"",reason,
             "","[]",now_ts(),now_ts(),"title_only",art.get("pub_date",""),1)
        )
        if cx.execute("SELECT changes()").fetchone()[0]: feed_saved += 1
    for art, score, reason in sug_arts:
        art_id = make_id("Financial Times", art["url"])
        cx.execute(
            'INSERT OR IGNORE INTO suggested_articles '
            '(title,url,source,score,reason,pub_date,status,added_at) '
            'VALUES (?,?,?,?,?,?,?,?)',
            (art["title"],art["url"],"Financial Times",
             score,reason,art.get("pub_date",""),"new",now_ts())
        )
        if cx.execute("SELECT changes()").fetchone()[0]: sug_saved += 1

log(f"\nSaved: {feed_saved} to Feed, {sug_saved} to Suggested")
log("Done. Run vps_push.py to sync to VPS.")

with open(BASE_DIR / "logs" / "backfill_preview.txt", "w") as f:
    f.write("\n".join(log_lines))
