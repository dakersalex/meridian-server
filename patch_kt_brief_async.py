import py_compile, tempfile, os

path = '/Users/alexdakers/meridian-server/server.py'
content = open(path).read()

start_idx = content.find('@app.route("/api/kt/brief", methods=["POST"])')
end_idx = content.find('\nif __name__', start_idx)

if start_idx == -1 or end_idx == -1:
    print('MARKERS NOT FOUND', start_idx, end_idx)
    exit(1)

print(f'Replacing chars {start_idx} to {end_idx}')

new_code = '''_kt_brief_jobs = {}

@app.route("/api/kt/brief", methods=["POST"])
def kt_brief():
    """Start async brief generation. Returns job_id immediately."""
    import uuid
    data = request.json or {}
    theme = data.get("theme", {})
    articles = data.get("articles", [])
    brief_type = data.get("type", "short")
    if not theme:
        return jsonify({"error": "no theme"}), 400

    job_id = str(uuid.uuid4())[:8]
    _kt_brief_jobs[job_id] = {"status": "running", "brief": None, "error": None}

    def _run():
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
            _kt_brief_jobs[job_id] = {"status": "error", "brief": None, "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})

@app.route("/api/kt/brief/status/<job_id>", methods=["GET"])
def kt_brief_status(job_id):
    """Poll for async kt/brief job result."""
    job = _kt_brief_jobs.get(job_id)
    if not job:
        return jsonify({"error": "unknown job"}), 404
    return jsonify(job)

'''

content = content[:start_idx] + new_code + content[end_idx:]
open(path, 'w').write(content)

tmp = tempfile.mktemp(suffix='.py')
open(tmp, 'w').write(content)
try:
    py_compile.compile(tmp, doraise=True)
    print('PATCH OK - syntax clean')
except py_compile.PyCompileError as e:
    print('SYNTAX ERROR:', e)
finally:
    os.unlink(tmp)
