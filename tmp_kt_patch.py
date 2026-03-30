"""Patch server.py: add KT incremental architecture tables + routes."""
from pathlib import Path
import sys, json

p = Path('/Users/alexdakers/meridian-server/server.py')
src = p.read_text()

# ── Patch 1: Add 3 new tables to init_db ─────────────────────────────────────
OLD1 = (
    "        # Add speaker_bio if missing from existing DBs\n"
    "        existing_iv_cols = [r[1] for r in cx.execute(\"PRAGMA table_info(interviews)\").fetchall()]\n"
    "        if 'speaker_bio' not in existing_iv_cols:\n"
    "            cx.execute(\"ALTER TABLE interviews ADD COLUMN speaker_bio TEXT DEFAULT ''\")\n"
    "        cx.commit()"
)

NEW1 = (
    "        # Add speaker_bio if missing from existing DBs\n"
    "        existing_iv_cols = [r[1] for r in cx.execute(\"PRAGMA table_info(interviews)\").fetchall()]\n"
    "        if 'speaker_bio' not in existing_iv_cols:\n"
    "            cx.execute(\"ALTER TABLE interviews ADD COLUMN speaker_bio TEXT DEFAULT ''\")\n"
    "        # -- Incremental Key Themes tables --\n"
    "        cx.execute('CREATE TABLE IF NOT EXISTS article_theme_tags '\n"
    "                   '(article_id TEXT NOT NULL, theme_name TEXT NOT NULL, tagged_at INTEGER NOT NULL,'\n"
    "                   ' PRIMARY KEY (article_id, theme_name))')\n"
    "        cx.execute('CREATE TABLE IF NOT EXISTS kt_themes '\n"
    "                   '(name TEXT PRIMARY KEY, emoji TEXT DEFAULT \"\", keywords TEXT DEFAULT \"[]\",'\n"
    "                   ' overview TEXT DEFAULT \"\", key_facts TEXT DEFAULT \"[]\",'\n"
    "                   ' subtopics TEXT DEFAULT \"[]\", subtopic_details TEXT DEFAULT \"{}\",'\n"
    "                   ' article_count INTEGER DEFAULT 0, last_updated INTEGER NOT NULL)')\n"
    "        cx.execute('CREATE TABLE IF NOT EXISTS kt_meta '\n"
    "                   '(key TEXT PRIMARY KEY, value TEXT NOT NULL)')\n"
    "        cx.commit()"
)

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    print('Patch 1 OK: KT tables added to init_db')
else:
    print('Patch 1 FAIL: boundary not found')
    idx = src.find('speaker_bio')
    print(repr(src[idx:idx+400]))
    sys.exit(1)

# ── Patch 2: Add new KT routes just before `if __name__` ─────────────────────
BOUNDARY = '\nif __name__ == "__main__":'

if BOUNDARY not in src:
    print('Patch 2 FAIL: if __name__ boundary not found')
    sys.exit(1)

NEW_ROUTES = r'''

# -- Incremental Key Themes routes --

_kt_seed_jobs = {}

@app.route("/api/kt/seed", methods=["POST"])
def kt_seed():
    """One-time (or reset) full seed. Wipes existing theme tables then seeds from scratch."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    _kt_seed_jobs[job_id] = {"status": "running", "progress": "Starting...", "error": None}

    def _run():
        try:
            with sqlite3.connect(DB_PATH) as cx:
                cx.execute("DELETE FROM article_theme_tags")
                cx.execute("DELETE FROM kt_themes")
                cx.execute("DELETE FROM kt_meta")
            log.info("kt/seed: wiped existing theme data")
            _kt_seed_jobs[job_id]["progress"] = "Fetching articles..."

            with sqlite3.connect(DB_PATH) as cx:
                cx.row_factory = sqlite3.Row
                arts = cx.execute(
                    "SELECT id, title, topic, tags, source FROM articles WHERE title!='' ORDER BY saved_at DESC"
                ).fetchall()
                interviews = cx.execute(
                    "SELECT id, title FROM interviews WHERE title!=''"
                ).fetchall()

            def _fmt_tags(t):
                if not t: return ""
                try: return ", ".join(json.loads(t))
                except: return ""

            art_lines = []
            for a in arts:
                line = "- [ART:" + a["id"] + "] " + (a["title"] or "")
                if a["topic"]: line += " [" + a["topic"] + "]"
                tags = _fmt_tags(a["tags"])
                if tags: line += " (" + tags + ")"
                art_lines.append(line)
            for iv in interviews:
                art_lines.append("- [IVW:" + str(iv["id"]) + "] " + (iv["title"] or "") + " [Interview]")

            total = len(art_lines)
            log.info(f"kt/seed: {total} items to process")
            _kt_seed_jobs[job_id]["progress"] = f"Sending {total} articles to Claude..."

            ctx = "\n".join(art_lines[:500])

            prompt = (
                "You are an intelligence analyst. Analyse these article titles and:\n"
                "1. Identify exactly 10 dominant intelligence themes from the corpus.\n"
                "2. Assign each article to 1-2 of those themes (use exact theme names).\n\n"
                'Respond ONLY with a valid JSON object (no markdown):\n'
                '{\n'
                '  "themes": [\n'
                '    {"name": "3-6 word name", "emoji": "emoji",\n'
                '     "keywords": ["kw1",...8-12],\n'
                '     "overview": "2-3 sentences",\n'
                '     "key_facts": [{"title": "short", "body": "fact with **bold** stats"}, ...10 items],\n'
                '     "subtopics": ["sub1",...5-7],\n'
                '     "subtopic_details": {"sub1": ["bullet",...4-6], ...}},\n'
                '    ...10 themes total\n'
                '  ],\n'
                '  "assignments": [\n'
                '    {"id": "ART:abc123", "themes": ["Theme Name One"]},\n'
                '    ...one entry per article\n'
                '  ]\n'
                '}\n\nARTICLES:\n' + ctx
            )

            resp = call_anthropic({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 12000,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=240, retries=1)

            raw = resp["content"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw
                raw = raw.rsplit("```", 1)[0]
            result = json.loads(raw)

            themes = result.get("themes", [])
            assignments = result.get("assignments", [])
            _kt_seed_jobs[job_id]["progress"] = f"Saving {len(themes)} themes and {len(assignments)} assignments..."

            ts = now_ts()
            theme_names = {t["name"] for t in themes}
            theme_counts = {t["name"]: 0 for t in themes}

            with sqlite3.connect(DB_PATH) as cx:
                for asgn in assignments:
                    aid_raw = asgn.get("id", "")
                    aid = aid_raw.replace("ART:", "").replace("IVW:", "")
                    for tname in asgn.get("themes", []):
                        if tname in theme_names:
                            theme_counts[tname] = theme_counts.get(tname, 0) + 1
                        try:
                            cx.execute(
                                "INSERT OR IGNORE INTO article_theme_tags (article_id, theme_name, tagged_at) VALUES (?,?,?)",
                                (aid, tname, ts)
                            )
                        except Exception as _e:
                            log.warning(f"kt/seed tag insert: {_e}")

                for t in themes:
                    tname = t.get("name", "")
                    cx.execute(
                        "INSERT OR REPLACE INTO kt_themes "
                        "(name, emoji, keywords, overview, key_facts, subtopics, subtopic_details, article_count, last_updated) "
                        "VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            tname,
                            t.get("emoji", ""),
                            json.dumps(t.get("keywords", [])),
                            t.get("overview", ""),
                            json.dumps(t.get("key_facts", [])),
                            json.dumps(t.get("subtopics", [])),
                            json.dumps(t.get("subtopic_details", {})),
                            theme_counts.get(tname, 0),
                            ts
                        )
                    )

                cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('last_seeded_at', ?)", (str(ts),))
                cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('article_count_at_seed', ?)", (str(total),))

            log.info(f"kt/seed: done -- {len(themes)} themes, {len(assignments)} assignments")
            _kt_seed_jobs[job_id] = {
                "status": "done", "progress": "Complete", "error": None,
                "theme_count": len(themes), "assignment_count": len(assignments)
            }
        except Exception as e:
            log.error(f"kt/seed job {job_id} error: {e}", exc_info=True)
            _kt_seed_jobs[job_id] = {"status": "error", "progress": str(e), "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/kt/seed/status/<job_id>", methods=["GET"])
def kt_seed_status(job_id):
    job = _kt_seed_jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)


@app.route("/api/kt/themes", methods=["GET"])
def kt_themes_route():
    """Return current themes from DB. Returns {seeded: false} if not yet seeded."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute("SELECT * FROM kt_themes ORDER BY article_count DESC").fetchall()
        meta_rows = cx.execute("SELECT key, value FROM kt_meta").fetchall()
    if not rows:
        return jsonify({"seeded": False, "themes": []})
    meta = {r["key"]: r["value"] for r in meta_rows}
    themes = []
    for r in rows:
        t = dict(r)
        for field in ("keywords", "key_facts", "subtopics"):
            try: t[field] = json.loads(t[field])
            except: t[field] = []
        try: t["subtopic_details"] = json.loads(t["subtopic_details"])
        except: t["subtopic_details"] = {}
        themes.append(t)
    return jsonify({"seeded": True, "themes": themes, "meta": meta})


@app.route("/api/kt/status", methods=["GET"])
def kt_status():
    """Return seeding state, counts, pending evolution suggestion."""
    with sqlite3.connect(DB_PATH) as cx:
        theme_count = cx.execute("SELECT COUNT(*) FROM kt_themes").fetchone()[0]
        tagged_count = cx.execute("SELECT COUNT(DISTINCT article_id) FROM article_theme_tags").fetchone()[0]
        total_arts = cx.execute("SELECT COUNT(*) FROM articles WHERE title!=''").fetchone()[0]
        meta_rows = cx.execute("SELECT key, value FROM kt_meta").fetchall()
    meta = {r[0]: r[1] for r in meta_rows}
    pending_evolution = json.loads(meta.get("pending_evolution", "null"))
    return jsonify({
        "seeded": theme_count > 0,
        "theme_count": theme_count,
        "tagged_articles": tagged_count,
        "total_articles": total_arts,
        "untagged_articles": total_arts - tagged_count,
        "last_seeded_at": meta.get("last_seeded_at"),
        "pending_evolution": pending_evolution,
    })


@app.route("/api/kt/tag-new", methods=["POST"])
def kt_tag_new():
    """Tag articles with no theme assignment yet. Haiku batches of 25."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        theme_rows = cx.execute("SELECT name FROM kt_themes").fetchall()
        if not theme_rows:
            return jsonify({"ok": False, "error": "not seeded"}), 400
        theme_names = [r["name"] for r in theme_rows]
        untagged = cx.execute(
            "SELECT a.id, a.title, a.topic, a.tags FROM articles a "
            "WHERE a.title != '' "
            "AND NOT EXISTS (SELECT 1 FROM article_theme_tags att WHERE att.article_id = a.id) "
            "ORDER BY a.saved_at DESC LIMIT 100"
        ).fetchall()
    if not untagged:
        return jsonify({"ok": True, "tagged": 0, "message": "nothing to tag"})

    def _run():
        import re as _re
        ts = now_ts()
        theme_list = json.dumps(theme_names)
        tagged_total = 0
        batch_size = 25
        arts = [dict(r) for r in untagged]
        for i in range(0, len(arts), batch_size):
            batch = arts[i:i + batch_size]
            batch_str = json.dumps([
                {"id": a["id"], "title": a["title"], "topic": a.get("topic", ""),
                 "tags": (json.loads(a["tags"]) if a.get("tags") else [])}
                for a in batch
            ])
            prompt = (
                "Given these 10 theme names: " + theme_list + "\n"
                "Assign each article to 1-2 themes. Use closest if none fit.\n"
                'Respond ONLY with a JSON array: [{"id":"abc","themes":["Theme One"]}]\n\n'
                "ARTICLES:\n" + batch_str
            )
            try:
                resp = call_anthropic({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }, timeout=30)
                raw = resp["content"][0]["text"].strip()
                m = _re.search(r'\[\s*\{[\s\S]*?\}\s*\]', raw)
                if not m:
                    log.warning("kt/tag-new: could not parse batch response")
                    continue
                assignments = json.loads(m.group(0))
                with sqlite3.connect(DB_PATH) as cx:
                    for asgn in assignments:
                        aid = asgn.get("id", "")
                        for tname in asgn.get("themes", []):
                            if tname in theme_names:
                                cx.execute(
                                    "INSERT OR IGNORE INTO article_theme_tags (article_id, theme_name, tagged_at) VALUES (?,?,?)",
                                    (aid, tname, ts)
                                )
                    for tname in theme_names:
                        cnt = cx.execute(
                            "SELECT COUNT(*) FROM article_theme_tags WHERE theme_name=?", (tname,)
                        ).fetchone()[0]
                        cx.execute("UPDATE kt_themes SET article_count=?, last_updated=? WHERE name=?",
                                   (cnt, ts, tname))
                tagged_total += len(assignments)
                log.info(f"kt/tag-new: batch {i // batch_size + 1} tagged {len(assignments)}")
            except Exception as e:
                log.warning(f"kt/tag-new: batch error: {e}")
        log.info(f"kt/tag-new: done -- {tagged_total} articles tagged")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "queued": len(untagged)})


@app.route("/api/kt/evolve", methods=["POST"])
def kt_evolve():
    """Check if any theme should be replaced. Writes suggestion to kt_meta as pending_evolution."""
    with sqlite3.connect(DB_PATH) as cx:
        cx.row_factory = sqlite3.Row
        themes = cx.execute("SELECT name, article_count FROM kt_themes ORDER BY article_count ASC").fetchall()
        if not themes:
            return jsonify({"ok": False, "error": "not seeded"}), 400
        potential = cx.execute(
            "SELECT theme_name, COUNT(*) as cnt FROM article_theme_tags "
            "WHERE theme_name LIKE 'potential:%' GROUP BY theme_name ORDER BY cnt DESC"
        ).fetchall()

    weakest = [dict(t) for t in themes[:3]]
    candidates = [dict(p) for p in potential if p["cnt"] >= 15]

    if not candidates:
        return jsonify({"ok": True, "suggestion": None,
                        "message": "No replacement candidate has 15+ articles yet"})

    suggestion = {
        "replace": weakest[0]["name"],
        "replace_count": weakest[0]["article_count"],
        "with": candidates[0]["theme_name"].replace("potential:", ""),
        "with_count": candidates[0]["cnt"],
        "detected_at": now_ts(),
    }
    with sqlite3.connect(DB_PATH) as cx:
        cx.execute("INSERT OR REPLACE INTO kt_meta (key, value) VALUES ('pending_evolution', ?)",
                   (json.dumps(suggestion),))
    log.info(f"kt/evolve: suggest replacing '{suggestion['replace']}' with '{suggestion['with']}'")
    return jsonify({"ok": True, "suggestion": suggestion})

'''

src = src.replace(BOUNDARY, NEW_ROUTES + '\nif __name__ == "__main__":', 1)
print('Patch 2 OK: KT routes added')

p.write_text(src)
print(f'Written {len(src)} chars to server.py')

# Quick syntax check
import subprocess
result = subprocess.run(['python3', '-c', f'import ast; ast.parse(open("{p}").read())'],
                       capture_output=True, text=True)
if result.returncode == 0:
    print('Syntax check: OK')
else:
    print('Syntax check FAIL:', result.stderr)
