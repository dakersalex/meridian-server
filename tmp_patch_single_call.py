"""
Patch server.py:
1. kt_brief route: use new _build_prompt / _build_article_context from brief_pdf
2. kt_brief_pdf route: accept optional 'text' field and pass as pregenerated_text
"""
import subprocess

path = "/Users/alexdakers/meridian-server/server.py"
with open(path, "r") as f:
    src = f.read()

# ── Patch 1: replace the kt_brief _run() body ────────────────────────────────
OLD_RUN = '''    def _run():
        try:
            art_context = "\\n\\n---\\n\\n".join(
                "SOURCE: " + a.get("source", "") + "\\nTITLE: " + a.get("title", "") + "\\nSUMMARY: " + a.get("summary", "")
                for a in articles
                if a.get("summary")
            )
            name = theme.get("name", "")
            emoji = theme.get("emoji", "")
            subtopics = theme.get("subtopics", [])

            if brief_type == "short":
                prompt = (
                    "You are a senior intelligence analyst. Write a concise intelligence brief on the theme \\"" + name + "\\" based on the articles below.\\n\\n"
                    "Structure:\\n## Executive Summary\\n[2-3 sentences overview]\\n\\n"
                    "## Key Developments\\n[5-7 bullet points]\\n\\n"
                    "## Strategic Implications\\n[2-3 paragraphs]\\n\\n"
                    "## Watch List\\n[3-5 things to watch]\\n\\n"
                    "ARTICLES:\\n" + art_context
                )
                max_tokens = 1500
            else:
                subtopic_sections = "\\n\\n".join(
                    "## " + st + "\\n[2-3 paragraphs of analytical prose]"
                    for st in subtopics
                )
                prompt = (
                    "You are a senior intelligence analyst. Write a comprehensive intelligence brief on \\"" + name + "\\".\\n\\n"
                    "Structure:\\n## " + emoji + " " + name + " — Intelligence Brief\\n\\n"
                    "## Executive Summary\\n[3-4 sentences]\\n\\n"
                    + subtopic_sections + "\\n\\n"
                    "## Cross-cutting Themes\\n[overarching patterns]\\n\\n"
                    "## Strategic Implications\\n[forward-looking analysis]\\n\\n"
                    "## Source Notes\\n[brief note on sources]\\n\\n"
                    "ARTICLES:\\n" + art_context
                )
                max_tokens = 4000

            resp = call_anthropic({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=180, retries=1)
            text = resp["content"][0]["text"]
            _kt_brief_jobs[job_id] = {"status": "done", "brief": text, "error": None}
            log.info(f"kt_brief job {job_id}: done")
        except Exception as e:
            log.error(f"kt_brief job {job_id} error: {e}")
            _kt_brief_jobs[job_id] = {"status": "error", "brief": None, "error": str(e)}'''

NEW_RUN = '''    def _run():
        try:
            from brief_pdf import _build_prompt, _build_article_context
            name = theme.get("name", "")
            subtopics = theme.get("subtopics", [])
            art_context = _build_article_context(articles, brief_type)
            prompt = _build_prompt(name, subtopics, art_context, brief_type)
            max_tokens = 1500 if brief_type == "short" else 4000

            resp = call_anthropic({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=180, retries=1)
            text = resp["content"][0]["text"]
            _kt_brief_jobs[job_id] = {"status": "done", "brief": text, "error": None}
            log.info(f"kt_brief job {job_id}: done")
        except Exception as e:
            log.error(f"kt_brief job {job_id} error: {e}")
            _kt_brief_jobs[job_id] = {"status": "error", "brief": None, "error": str(e)}'''

assert OLD_RUN in src, "kt_brief _run not found"
src = src.replace(OLD_RUN, NEW_RUN, 1)

# ── Patch 2: kt_brief_pdf route — accept optional pre-generated text ─────────
OLD_PDF = '''    job_id = str(uuid.uuid4())[:8]
    _bpdf.start_pdf_job(job_id, theme, articles, brief_type, str(DB_PATH), str(BASE_DIR))
    return jsonify({"ok": True, "job_id": job_id})'''

NEW_PDF = '''    job_id = str(uuid.uuid4())[:8]
    # Accept pre-generated text from the modal brief (single-call architecture).
    # If the frontend passes the text it already has, skip the Sonnet call.
    pregenerated_text = data.get("text") or None
    _bpdf.start_pdf_job(job_id, theme, articles, brief_type, str(DB_PATH), str(BASE_DIR),
                        pregenerated_text=pregenerated_text)
    return jsonify({"ok": True, "job_id": job_id})'''

assert OLD_PDF in src, "kt_brief_pdf job start not found"
src = src.replace(OLD_PDF, NEW_PDF, 1)

with open(path, "w") as f:
    f.write(src)

result = subprocess.run(["python3", "-m", "py_compile", path], capture_output=True, text=True)
if result.returncode == 0:
    print("server.py COMPILE_OK")
else:
    print("COMPILE_FAIL:", result.stderr)
