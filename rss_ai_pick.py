#!/usr/bin/env python3
"""
RSS-based AI pick pipeline — replaces Playwright-dependent scraping.
Fetches articles from FT, Economist, and FA RSS feeds (public, no auth),
scores them with Haiku, and routes to Feed (auto_saved) or Suggested.

This is a standalone function to be added to server.py.
"""
import json, sqlite3, urllib.request, xml.etree.ElementTree as ET, hashlib, time, logging, re
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "meridian.db"

log = logging.getLogger("meridian")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RSS_FEEDS = {
    "Financial Times": [
        "https://www.ft.com/rss/home",
        "https://www.ft.com/world?format=rss",
        "https://www.ft.com/markets?format=rss",
        "https://www.ft.com/global-economy?format=rss",
        "https://www.ft.com/companies?format=rss",
        "https://www.ft.com/technology?format=rss",
    ],
    "The Economist": [
        "https://www.economist.com/leaders/rss.xml",
        "https://www.economist.com/briefing/rss.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.economist.com/international/rss.xml",
        "https://www.economist.com/business/rss.xml",
        "https://www.economist.com/the-world-this-week/rss.xml",
    ],
    "Foreign Affairs": [
        "https://www.foreignaffairs.com/rss.xml",
    ],
}

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def make_id(source, url):
    return hashlib.sha1(f"{source}:{url}".encode()).hexdigest()[:16]

def fetch_rss(url):
    """Fetch and parse a single RSS feed. Returns list of dicts."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        channel = root.find('channel')
        if channel is None:
            return []
        items = channel.findall('item')
        articles = []
        for item in items:
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            pub_el = item.find('pubDate')
            
            title = (title_el.text or "").strip() if title_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            desc = (desc_el.text or "").strip() if desc_el is not None else ""
            pub = (pub_el.text or "").strip() if pub_el is not None else ""
            
            if not title or not link:
                continue
            
            # Clean URL
            link = link.split('?')[0]
            
            # Parse pub_date to ISO
            pub_date = ""
            if pub:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub)
                    pub_date = dt.strftime('%Y-%m-%d')
                except:
                    m = re.search(r'(\d{4})[/-](\d{2})[/-](\d{2})', pub)
                    if m:
                        pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            
            articles.append({
                "title": title,
                "url": link,
                "description": desc,
                "pub_date": pub_date,
            })
        return articles
    except Exception as e:
        log.warning(f"RSS fetch failed for {url}: {e}")
        return []


def rss_ai_pick():
    """Main RSS-based AI pick function."""
    # Gate: twice daily
    now_h = datetime.now().hour
    gate_key = 'rss_pick_morning' if now_h < 13 else 'rss_pick_midday'
    today = datetime.now().strftime('%Y-%m-%d')
    
    with sqlite3.connect(str(DB_PATH)) as cx:
        cx.execute("CREATE TABLE IF NOT EXISTS kt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        last = cx.execute("SELECT value FROM kt_meta WHERE key=?", (gate_key,)).fetchone()
    if last and last[0] == today:
        log.info(f"RSS pick: already ran [{gate_key}] — skipping")
        return
    
    # Build known URLs
    with sqlite3.connect(str(DB_PATH)) as cx:
        all_urls = set(r[0] for r in cx.execute("SELECT url FROM articles WHERE url!=''").fetchall())
        suggested_urls = set(r[0] for r in cx.execute("SELECT url FROM suggested_articles WHERE url!=''").fetchall())
    known = all_urls | suggested_urls
    
    # Fetch all RSS feeds
    candidates = []
    cutoff = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d')
    
    for source, feeds in RSS_FEEDS.items():
        source_count = 0
        for feed_url in feeds:
            articles = fetch_rss(feed_url)
            for art in articles:
                url = art['url']
                if url in known:
                    continue
                # Only recent articles
                if art['pub_date'] and art['pub_date'] < cutoff:
                    continue
                known.add(url)  # dedup across feeds
                candidates.append({
                    "title": art['title'],
                    "url": url,
                    "source": source,
                    "pub_date": art['pub_date'],
                    "standfirst": art['description'],
                })
                source_count += 1
        log.info(f"RSS pick: {source} — {source_count} new candidates")
    
    if not candidates:
        log.info("RSS pick: no new candidates")
        with sqlite3.connect(str(DB_PATH)) as cx:
            cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (gate_key, today))
        return
    
    log.info(f"RSS pick: {len(candidates)} total candidates — scoring with Haiku")
    
    # Build interest profile
    with sqlite3.connect(str(DB_PATH)) as cx:
        rows = cx.execute("SELECT topic, tags FROM articles ORDER BY saved_at DESC LIMIT 150").fetchall()
    counts = {}
    for topic, tags in rows:
        if topic: counts[topic] = counts.get(topic, 0) + 1
        try:
            for t in json.loads(tags or "[]"):
                counts[t] = counts.get(t, 0) + 1
        except: pass
    interests = ", ".join(sorted(counts, key=lambda x: -counts[x])[:15]) or "geopolitics, economics, finance, markets"
    
    # Load taste titles
    with sqlite3.connect(str(DB_PATH)) as cx:
        tt_row = cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'").fetchone()
    taste_titles = json.loads(tt_row[0]) if tt_row else []
    taste_str = "\n".join(f"- {t}" for t in taste_titles[:50])
    
    # Score with Haiku (cheaper than Sonnet, good enough for scoring)
    creds = json.loads((BASE_DIR / "credentials.json").read_text())
    api_key = creds.get("anthropic_api_key", "")
    if not api_key:
        log.warning("RSS pick: no API key")
        return
    
    articles_list = json.dumps([
        {"title": a["title"], "url": a["url"], "source": a["source"],
         "standfirst": a.get("standfirst", "")}
        for a in candidates
    ])
    
    prompt = (
        "You are scoring news articles for a senior intelligence analyst.\n"
        "INTERESTS: " + interests + ".\n\n"
        + ("RECENT SAVES (calibrate taste):\n" + taste_str + "\n\n" if taste_str else "")
        + "Score each candidate 0-10:\n"
        "9-10: BREAKING — war, sanctions, central bank decision, major diplomatic event, market shock.\n"
        "7-8: High-quality analysis on geopolitics, markets, economics, AI policy.\n"
        "6: Relevant essay or analysis.\n"
        "0-5: Not relevant — lifestyle, sport, celebrity, local politics.\n"
        "A thoughtful essay = 6-7 max. Only concrete events = 9-10.\n"
        f"Respond ONLY with a JSON array of EXACTLY {len(candidates)} integers:\n"
        + "\nCandidate articles:\n" + articles_list
    )
    
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        log.warning(f"RSS pick: API call failed: {e}")
        return
    
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    if not text:
        log.warning("RSS pick: empty response")
        return
    
    # Parse scores
    text = text.strip()
    if "```" in text:
        text = text.split("```", 2)[1]
        if text.startswith("json"): text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    
    m = re.search(r'\[[\s\S]*\]', text)
    raw_json = m.group(0) if m else '[]'
    try:
        scores = json.loads(raw_json)
    except:
        scores = [int(x) for x in re.findall(r'\b([0-9]|10)\b', raw_json)]
    
    log.info(f"RSS pick: got {len(scores)} scores")
    
    # Route by score
    now_ts = int(time.time() * 1000)
    feed_count = 0
    suggested_count = 0
    
    with sqlite3.connect(str(DB_PATH)) as cx:
        for i, art in enumerate(candidates):
            if i >= len(scores): break
            score = scores[i] if isinstance(scores[i], int) else 0
            
            aid = make_id(art['source'], art['url'])
            feed_threshold = 7 if art['source'] == "Foreign Affairs" else 8
            
            if score >= feed_threshold:
                # Auto-save to feed
                cx.execute("""INSERT OR IGNORE INTO articles
                    (id, source, url, title, body, summary, topic, tags,
                     saved_at, fetched_at, status, pub_date, auto_saved)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (aid, art['source'], art['url'], art['title'],
                     "", "", "", "[]", now_ts, now_ts,
                     "title_only", art.get('pub_date', ''), 1))
                feed_count += 1
                log.info(f"RSS pick: FEED score={score} [{art['source']}] {art['title'][:55]}")
                
                # Log to agent_log
                cx.execute("INSERT INTO agent_log (article_id, title, url, score, reason, saved_at) VALUES (?,?,?,?,?,?)",
                    (aid, art['title'], art['url'], score, f"RSS pick score={score}", now_ts))
            
            elif score >= 6:
                # Add to suggested
                cx.execute("""INSERT OR IGNORE INTO suggested_articles
                    (title, url, source, score, reason, added_at, status, pub_date, preview)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (art['title'], art['url'], art['source'], score,
                     f"RSS pick", now_ts, "new", art.get('pub_date', ''),
                     art.get('standfirst', '')))
                suggested_count += 1
        
        # Mark gate
        cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES (?, ?)", (gate_key, today))
        cx.commit()
    
    log.info(f"RSS pick: done — {feed_count} to feed, {suggested_count} to suggested")
    
    # Trigger body fetching + enrichment for the auto-saved title_only articles
    if feed_count > 0:
        try:
            urllib.request.urlopen(
                urllib.request.Request("http://localhost:4242/api/enrich-title-only", method="POST",
                    headers={"Content-Type": "application/json"}, data=b"{}"),
                timeout=5
            )
            log.info("RSS pick: triggered body fetch + enrichment for new articles")
        except:
            pass  # Fire and forget


if __name__ == "__main__":
    rss_ai_pick()
