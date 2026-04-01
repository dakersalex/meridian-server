"""
Fix kt/seed Call 3: generate key_facts one theme at a time using Haiku,
not all 10 at once with Sonnet. Much faster, no timeout.
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/server.py')
src = p.read_text()

OLD = '''\
            # ── Call 3: Generate key_facts + subtopic_details for all themes ──
            _kt_seed_jobs[job_id]["progress"] = "Generating key facts for each theme..."
            try:
                theme_names_list = json.dumps([t["name"] for t in themes])
                kf_prompt = (
                    "For each of these 10 intelligence themes, generate key_facts and subtopic_details.\\n"
                    "Themes: " + theme_names_list + "\\n\\n"
                    "For each theme return a JSON object with:\\n"
                    "- name (exact theme name as given)\\n"
                    "- key_facts (array of exactly 10 objects, each with 'title' (short label) "
                    "and 'body' (1-2 sentences; use **bold** for key figures/stats))\\n"
                    "- subtopic_details (object mapping subtopic name to array of 4-6 bullet strings)\\n\\n"
                    "Subtopics for each theme:\\n" +
                    "\\n".join(t["name"] + ": " + ", ".join(t.get("subtopics", [])) for t in themes) +
                    "\\n\\nReturn ONLY a valid JSON array of 10 objects. No markdown, no preamble."
                )
                kf_resp = call_anthropic({
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": kf_prompt}]
                }, timeout=120, retries=1)
                kf_raw = kf_resp["content"][0]["text"].strip()
                if kf_raw.startswith("```"):
                    kf_raw = kf_raw.split("\\n", 1)[1] if "\\n" in kf_raw else kf_raw
                    kf_raw = kf_raw.rsplit("```", 1)[0]
                kf_data = json.loads(kf_raw)
                kf_map = {item["name"]: item for item in kf_data}
                with sqlite3.connect(DB_PATH) as cx:
                    for t in themes:
                        kf_item = kf_map.get(t["name"], {})
                        kf = kf_item.get("key_facts", [])
                        sd = kf_item.get("subtopic_details", {})
                        cx.execute(
                            "UPDATE kt_themes SET key_facts=?, subtopic_details=? WHERE name=?",
                            (json.dumps(kf), json.dumps(sd), t["name"])
                        )
                log.info(f"kt/seed: key_facts enrichment done for {len(kf_data)} themes")
            except Exception as kf_err:
                log.warning(f"kt/seed: key_facts generation failed (non-fatal): {kf_err}")
'''

NEW = '''\
            # ── Call 3: Generate key_facts + subtopic_details per theme (Haiku, one at a time) ──
            _kt_seed_jobs[job_id]["progress"] = "Generating key facts for each theme..."
            kf_ok = 0
            for ti, t in enumerate(themes):
                try:
                    _kt_seed_jobs[job_id]["progress"] = f"Generating key facts ({ti+1}/10): {t['name'][:40]}..."
                    subs = t.get("subtopics", [])
                    kf_prompt = (
                        "Generate key_facts and subtopic_details for this intelligence theme.\\n\\n"
                        "Theme: " + t["name"] + "\\n"
                        "Overview: " + t.get("overview", "") + "\\n"
                        "Subtopics: " + ", ".join(subs) + "\\n\\n"
                        "Return a JSON object with exactly these fields:\\n"
                        "- key_facts: array of exactly 10 objects, each with 'title' (short label, "
                        "max 6 words) and 'body' (1-2 sentences; use **bold** for key figures/stats)\\n"
                        "- subtopic_details: object mapping each subtopic name to array of 4-6 bullet strings\\n\\n"
                        "Return ONLY a valid JSON object. No markdown, no preamble."
                    )
                    kf_resp = call_anthropic({
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": kf_prompt}]
                    }, timeout=30, retries=1)
                    kf_raw = kf_resp["content"][0]["text"].strip()
                    if kf_raw.startswith("```"):
                        kf_raw = kf_raw.split("\\n", 1)[1] if "\\n" in kf_raw else kf_raw
                        kf_raw = kf_raw.rsplit("```", 1)[0]
                    kf_item = json.loads(kf_raw)
                    kf = kf_item.get("key_facts", [])
                    sd = kf_item.get("subtopic_details", {})
                    with sqlite3.connect(DB_PATH) as cx:
                        cx.execute(
                            "UPDATE kt_themes SET key_facts=?, subtopic_details=? WHERE name=?",
                            (json.dumps(kf), json.dumps(sd), t["name"])
                        )
                    kf_ok += 1
                except Exception as kf_err:
                    log.warning(f"kt/seed: key_facts failed for '{t['name']}' (non-fatal): {kf_err}")
            log.info(f"kt/seed: key_facts enrichment done for {kf_ok}/10 themes")
'''

assert OLD in src, "OLD not found"
src = src.replace(OLD, NEW, 1)
p.write_text(src)
print("Patched OK")
