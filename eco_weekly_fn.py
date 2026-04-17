def ai_pick_economist_weekly():
    """Scrape The Economist weekly editions via CDP and score with Sonnet.

    Sources: /weeklyedition/archive -> 2 most recent edition URLs -> all articles.
    Scores ALL articles (not just unsaved) so we always have enough candidates.
    Gate: per-edition key in kt_meta so each edition is only scored once.
    Scheduled: 22:00 UTC Thursdays. Can be triggered manually anytime.
    """
    import json as _j
    import subprocess as _sp
    import tempfile as _tf
    import os as _os
    import re as _re
    import hashlib as _hh

    # ── Build taste profile ───────────────────────────────────────────────────
    with sqlite3.connect(DB_PATH) as _cx:
        _ft_row  = _cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_followed_topics'").fetchone()
        _tt_row  = _cx.execute("SELECT value FROM kt_meta WHERE key='ai_pick_taste_titles'").fetchone()
        _known   = set(r[0] for r in _cx.execute("SELECT url FROM articles WHERE url!=''").fetchall())
        _known  |= set(r[0] for r in _cx.execute("SELECT url FROM suggested_articles WHERE url!=''").fetchall())
    _followed   = _j.loads(_ft_row[0]) if _ft_row else []
    _taste      = _j.loads(_tt_row[0]) if _tt_row else []
    _topics_str = ", ".join(_followed) if _followed else "geopolitics, economics, finance, markets"
    _taste_str  = "\n".join(f"- {t}" for t in _taste[:50])

    # ── CDP scrape subprocess ─────────────────────────────────────────────────
    _profile = str(BASE_DIR / "eco_chrome_profile")
    _lock    = BASE_DIR / "eco_chrome_profile" / "SingletonLock"
    if _lock.exists(): _lock.unlink()

    _out = _tf.NamedTemporaryFile(mode='w', suffix='.json', delete=False, dir='/tmp')
    _out_path = _out.name
    _out.close()

    # Write the subprocess script
    _sub_path = str(BASE_DIR / "eco_weekly_sub.py")

    _proc = _sp.run(
        ["python3", _sub_path, _profile, _out_path],
        timeout=180, capture_output=True, text=True
    )
    log.info("Economist weekly scrape stderr: " + _proc.stderr[-600:])

    if _proc.returncode != 0:
        log.error("Economist weekly scrape failed: " + _proc.stderr[-300:])
        with sqlite3.connect(DB_PATH) as _cx:
            _cx.execute("INSERT OR REPLACE INTO kt_meta (key,value) VALUES (?,?)",
                       ("eco_cdp_status", "DOWN:" + datetime.now().strftime("%Y-%m-%d %H:%M")))
        return [], []

    try:
        _result = _j.loads(open(_out_path).read())
    except Exception as e:
        log.error(f"Economist weekly JSON parse error: {e}")
        return [], []
    finally:
        try: _os.unlink(_out_path)
        except: pass

    _edition_urls = _result.get("edition_urls", [])
    _all_candidates = _result.get("articles", [])
    log.info(f"Economist weekly: {len(_all_candidates)} candidates from editions: {_edition_urls}")

    if not _all_candidates:
        log.info("Economist weekly: no candidates found")
        return [], []

    with sqlite3.connect(DB_PATH) as _cx:
        _cx.execute("INSERT OR REPLACE INTO kt_meta (key,value) VALUES (?,?)",
                   ("eco_cdp_status", "OK:" + datetime.now().strftime("%Y-%m-%d %H:%M")))

    _feed_articles = []
    _suggested_out = []

    for _edition_url in _edition_urls:
        _m = _re.search(r'weeklyedition/([0-9-]+)', _edition_url)
        _edition_str = _m.group(1) if _m else _edition_url
        _gate_key = f"ai_pick_economist_weekly_{_edition_str}"

        with sqlite3.connect(DB_PATH) as _gx:
            _gx.execute("CREATE TABLE IF NOT EXISTS kt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            _already = _gx.execute("SELECT value FROM kt_meta WHERE key=?", (_gate_key,)).fetchone()
        if _already:
            log.info(f"Economist weekly: already scored edition {_edition_str} — skipping")
            continue

        _edition_candidates = [c for c in _all_candidates if c.get("edition") == _edition_str]
        log.info(f"Economist weekly: scoring {len(_edition_candidates)} candidates for {_edition_str}")
        if not _edition_candidates:
            continue

        # ── Score with Haiku ──────────────────────────────────────────────────
        _prompt_lines = []
        for _i, _c in enumerate(_edition_candidates):
            _sf = f" — {_c['standfirst']}" if _c.get("standfirst") else ""
            _tag = "★ " if _c.get("url") in _known else ""
            _prompt_lines.append(f"{_i}: {_tag}{_c['title']}{_sf}")

        _prompt = f"""You are scoring Economist articles for an analyst interested in: {_topics_str}.

Recent saves (taste profile):
{_taste_str}

Score each article 1-10 based on relevance. ★ = already saved (still score it).

Articles ({len(_edition_candidates)} total):
{chr(10).join(_prompt_lines)}

Respond with EXACTLY {len(_edition_candidates)} integers, one per line, nothing else."""

        try:
            import urllib.request as _ur
            with sqlite3.connect(DB_PATH) as _kx:
                _creds = _j.loads(_kx.execute("SELECT value FROM kt_meta WHERE key='anthropic_credentials'").fetchone()[0])
            _api_key = _creds.get("api_key", "")
            _payload = _j.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": _prompt}]
            }).encode()
            _req = _ur.Request(
                "https://api.anthropic.com/v1/messages",
                data=_payload,
                headers={"Content-Type": "application/json",
                         "x-api-key": _api_key,
                         "anthropic-version": "2023-06-01"},
                method="POST"
            )
            with _ur.urlopen(_req, timeout=60) as _resp:
                _resp_data = _j.loads(_resp.read())
            _text = _resp_data["content"][0]["text"].strip()
            _scores = [int(x.strip()) for x in _text.split('\n') if x.strip().lstrip('-').isdigit()]
            log.info(f"Economist weekly: Sonnet returned {len(_scores)} scores for {_edition_str}")
        except Exception as e:
            log.error(f"Economist weekly scoring error: {e}")
            continue

        if len(_scores) != len(_edition_candidates):
            log.warning(f"Economist weekly: score mismatch {len(_scores)} vs {len(_edition_candidates)}")
            _scores = (_scores + [0] * len(_edition_candidates))[:len(_edition_candidates)]

        # ── Route ─────────────────────────────────────────────────────────────
        for _c, _score in zip(_edition_candidates, _scores):
            _url   = _c.get("url", "")
            _title = _c.get("title", "")
            log.info(f"Economist weekly: score={_score} {_title[:60]}")

            if _score >= 8:
                if _url not in _known:
                    _aid = _hh.sha1(f"The Economist:{_url}".encode()).hexdigest()[:16]
                    with sqlite3.connect(DB_PATH) as _fx:
                        _fx.execute(
                            "INSERT OR IGNORE INTO articles "
                            "(id,source,url,title,body,summary,topic,tags,saved_at,fetched_at,status,pub_date,auto_saved) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (_aid, "The Economist", _url, _title, "", "", "", "[]",
                             now_ts(), now_ts(), "title_only", "", 1)
                        )
                    _feed_articles.append({"title": _title, "url": _url, "source": "The Economist"})
                    _known.add(_url)
                else:
                    log.info(f"Economist weekly: score={_score} already in library, skip insert")

            elif _score >= 6:
                if _url not in _known:
                    _suggested_out.append({
                        "title": _title, "url": _url, "source": "The Economist",
                        "score": _score, "reason": _c.get("standfirst", ""),
                        "pub_date": ""
                    })

        # Mark edition done
        with sqlite3.connect(DB_PATH) as _gx:
            _gx.execute("INSERT OR REPLACE INTO kt_meta (key,value) VALUES (?,?)",
                       (_gate_key, datetime.now().isoformat()))

    if _feed_articles:
        enrich_batch([a for a in _feed_articles])
        push_to_vps(_feed_articles)

    if _suggested_out:
        save_suggested_snapshot(_suggested_out)

    log.info(f"Economist weekly complete: {len(_feed_articles)} -> Feed, {len(_suggested_out)} -> Suggested")
    return _feed_articles, _suggested_out

