with open('/Users/alexdakers/meridian-server/server.py', 'r') as f:
    src = f.read()

# Fix 1: increase max_tokens for Call 3 key_facts from 1500 to 2500
OLD1 = '''                    kf_resp = call_anthropic({
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 1500,
                        "messages": [{"role": "user", "content": kf_prompt}]
                    }, timeout=30, retries=1)'''

NEW1 = '''                    kf_resp = call_anthropic({
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 2500,
                        "messages": [{"role": "user", "content": kf_prompt}]
                    }, timeout=45, retries=1)'''

# Fix 2: hardcoded /10 in progress message
OLD2 = '                    _kt_seed_jobs[job_id]["progress"] = f"Generating key facts ({ti+1}/10): {t[\'name\'][:40]}..."'
NEW2 = '                    _kt_seed_jobs[job_id]["progress"] = f"Generating key facts ({ti+1}/{len(themes)}): {t[\'name\'][:40]}..."'

# Fix 3: hardcoded /10 in enrichment done log
OLD3 = '            log.info(f"kt/seed: key_facts enrichment done for {kf_ok}/10 themes")'
NEW3 = '            log.info(f"kt/seed: key_facts enrichment done for {kf_ok}/{len(themes)} themes")'

results = []
for old, new, label in [(OLD1, NEW1, "max_tokens 1500->2500 + timeout 30->45"),
                         (OLD2, NEW2, "progress /10 -> /{len(themes)}"),
                         (OLD3, NEW3, "log /10 -> /{len(themes)}")]:
    if old in src:
        src = src.replace(old, new)
        results.append(f"OK: {label}")
    else:
        results.append(f"FAILED: {label}")

with open('/Users/alexdakers/meridian-server/server.py', 'w') as f:
    f.write(src)

for r in results:
    print(r)
