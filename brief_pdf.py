"""
brief_pdf.py - Intelligence Brief PDF generation for Meridian.
"""
import io, re, sqlite3, logging, threading, datetime, urllib.request, json
from pathlib import Path

log = logging.getLogger("meridian")

# Headings that should never receive charts (lowercase)
_NO_CHART_SECTIONS = {
    "executive summary", "cross-cutting themes", "source notes",
    "strategic implications", "watch list", "key developments", "overview"
}

# Minimum keyword-overlap score for a chart to qualify for a section
_MIN_SCORE = 2

# Cross-brief similarity threshold — reject chart if description too similar
# to one already placed elsewhere in the brief
_CROSS_BRIEF_SIMILARITY = 0.5


def _tok(text):
    return set(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())


def _desc_similar(a, b, threshold=0.6):
    """True if two description strings share > threshold fraction of tokens."""
    ta, tb = _tok(a), _tok(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / max(len(ta), len(tb)) > threshold


def _dedup_by_description(charts):
    """Remove near-duplicate images (same chart pushed twice)."""
    kept = []
    for c in charts:
        desc = c.get("description", "")
        if not any(_desc_similar(desc, k.get("description", "")) for k in kept):
            kept.append(c)
    return kept


def score_charts_for_section(section_heading, section_text, charts,
                              placed_descriptions, max_charts=2,
                              min_score=_MIN_SCORE):
    """Score candidate charts against a section and return the top matches."""
    if section_heading.lower().strip() in _NO_CHART_SECTIONS:
        return []
    h_clean = section_heading.strip()
    if h_clean.startswith("#") or "intelligence brief" in h_clean.lower():
        return []

    section_tokens = _tok(section_heading + " " + section_text)
    if not section_tokens:
        return []

    scored = []
    for c in charts:
        if any(_desc_similar(c.get("description", ""), pd,
                             threshold=_CROSS_BRIEF_SIMILARITY)
               for pd in placed_descriptions):
            continue
        score = (len(_tok(c.get("insight", "")) & section_tokens) * 2
                 + len(_tok(c.get("description", "")) & section_tokens))
        if score >= min_score:
            scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    result, seen_articles = [], set()
    for _, c in scored:
        aid = c.get("article_id")
        if aid not in seen_articles:
            seen_articles.add(aid)
            result.append(c)
        if len(result) >= max_charts:
            break

    # Never return exactly 1 chart — either 0 or 2+
    if len(result) == 1:
        return []
    return result


def _build_prompt(theme_name, subtopics, article_context, brief_type):
    """
    Build the brief generation prompt.

    Design principles:
    - Works across all Meridian themes (geopolitics, markets, technology, corporate, etc.)
    - Explicitly requests statistics and figures where available in source articles
    - Follows intelligence analyst register: lead with finding, support with evidence, state implication
    - Does NOT hallucinate — only uses figures present in the source material
    - Section instruction guides depth without prescribing domain-specific content
    """
    SECTION_INSTRUCTION = (
        "[2-3 paragraphs of analytical prose. "
        "Lead each paragraph with the key analytical finding. "
        "Support findings with specific figures, percentages, prices, quantities "
        "or dates from the source articles where available — these anchor the analysis. "
        "Close with the forward-looking implication. "
        "Only cite statistics that appear in the articles provided.]"
    )

    if brief_type == "short":
        return (
            f'You are a senior intelligence analyst. '
            f'Write a concise intelligence brief on "{theme_name}".\n\n'
            f"Where source articles contain specific figures, percentages, prices or data points, "
            f"incorporate them precisely — one or two per section is sufficient to ground the analysis. "
            f"Do not invent statistics.\n\n"
            f"Structure:\n"
            f"## Executive Summary\n[2-3 sentences capturing the core assessment]\n\n"
            f"## Key Developments\n[5-7 bullet points, each with a specific figure or date where available]\n\n"
            f"## Strategic Implications\n{SECTION_INSTRUCTION}\n\n"
            f"## Watch List\n[3-5 specific things to monitor in the coming weeks]\n\n"
            f"ARTICLES:\n{article_context}"
        )
    else:
        subtopic_sections = "\n\n".join(
            f"## {s}\n{SECTION_INSTRUCTION}" for s in subtopics)
        return (
            f'You are a senior intelligence analyst. '
            f'Write a comprehensive intelligence brief on "{theme_name}".\n\n'
            f"IMPORTANT: Start directly with the Executive Summary. "
            f"Do NOT include a title heading or overview section.\n\n"
            f"Where source articles contain specific figures, percentages, prices, "
            f"quantities or dates, incorporate them precisely into your analysis — "
            f"aim for one or two concrete data points per section to anchor the assessment. "
            f"Do not invent or estimate statistics; only use figures present in the articles.\n\n"
            f"Structure:\n"
            f"## Executive Summary\n"
            f"[3-4 sentences. State the overarching assessment directly — "
            f"what is happening, why it matters, and what the key tension or implication is.]\n\n"
            + subtopic_sections + "\n\n"
            f"## Cross-cutting Themes\n"
            f"[3-4 analytical observations that cut across the subtopics above — "
            f"patterns, paradoxes or structural dynamics that individual sections don't fully capture]\n\n"
            f"## Strategic Implications\n"
            f"[2-3 paragraphs of forward-looking analysis. "
            f"What does the current trajectory lead to? "
            f"What are the key uncertainties and decision points?]\n\n"
            f"ARTICLES:\n{article_context}"
        )


def _build_article_context(articles, brief_type):
    """
    Build richer article context by including the first 400 chars of body text
    alongside the summary. This preserves specific statistics that get lost
    when only summaries are used.
    """
    MAX_ARTICLES = 30 if brief_type == "short" else 60
    BODY_EXCERPT = 400  # chars of body to include alongside summary

    parts = []
    for a in articles[:MAX_ARTICLES]:
        if not a.get("summary"):
            continue
        snippet = f"SOURCE: {a.get('source', '')}\nTITLE: {a.get('title', '')}\n"
        snippet += f"SUMMARY: {a.get('summary', '')}"
        # Append a body excerpt if available and non-trivial
        body = (a.get("body") or "").strip()
        if body and len(body) > 100:
            excerpt = body[:BODY_EXCERPT].rsplit(" ", 1)[0]  # trim at word boundary
            snippet += f"\nEXCERPT: {excerpt}…"
        parts.append(snippet)

    return "\n\n---\n\n".join(parts)


def build_brief_pdf(theme, articles, brief_text, brief_type="full", db_path=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
        HRFlowable, Image as RLImage, Table, TableStyle, KeepTogether)
    from reportlab.lib.colors import HexColor
    AMBER = HexColor("#c4783a"); MID = HexColor("#555555"); LIGHT = HexColor("#888888")
    DARK = HexColor("#1a1a1a"); BORD = HexColor("#ddd8cc")

    def S(name, **kw):
        d = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=DARK,
                 spaceAfter=0, spaceBefore=0)
        d.update(kw); return ParagraphStyle(name, **d)

    SE = S("e", fontSize=7,  textColor=AMBER, fontName="Helvetica-Bold",
           letterSpacing=1.5, spaceAfter=4)
    ST = S("t", fontSize=22, fontName="Helvetica-Bold", leading=26, spaceAfter=6)
    SM = S("m", fontSize=8,  textColor=LIGHT, spaceAfter=16)
    SS = S("s", fontSize=8,  textColor=AMBER, fontName="Helvetica-Bold",
           letterSpacing=1.2, spaceAfter=8, spaceBefore=20)
    SB = S("b", fontSize=10, leading=16, textColor=MID, spaceAfter=10)
    SF = S("f", fontSize=7,  textColor=LIGHT, letterSpacing=0.8)

    # ── Fetch candidate charts ─────────────────────────────────────────────────
    article_ids = [a.get("id") for a in articles if a.get("id")]
    all_charts = []
    if article_ids and db_path:
        ph = ",".join("?" * len(article_ids))
        with sqlite3.connect(db_path) as cx:
            rows = cx.execute(
                f"SELECT id, article_id, caption, description, insight, image_data, width, height "
                f"FROM article_images WHERE article_id IN ({ph}) "
                "AND insight != '' AND insight IS NOT NULL AND image_data IS NOT NULL",
                article_ids).fetchall()
        for r in rows:
            all_charts.append({"id": r[0], "article_id": r[1], "caption": r[2],
                                "description": r[3], "insight": r[4],
                                "image_data": r[5], "width": r[6], "height": r[7]})

    all_charts = _dedup_by_description(all_charts)
    log.info(f"Brief PDF: {len(all_charts)} distinct charts for {len(article_ids)} articles")

    # ── Parse sections ─────────────────────────────────────────────────────────
    def parse_sections(text):
        parts = re.split(r"\n(?=## )", text.strip())
        secs = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.startswith("## "):
                lines2 = part[3:].split("\n", 1)
                h = lines2[0].strip()
                b = lines2[1].strip() if len(lines2) > 1 else ""
            else:
                h = "Overview"; b = part
            if b:
                secs.append({"heading": h, "body": b})
        return secs

    sections = parse_sections(brief_text)
    sources = sorted(set(a.get("source", "") for a in articles if a.get("source", "")))

    # ── Pre-assign charts ──────────────────────────────────────────────────────
    MAX_TOTAL = 14
    MAX_PER_SECTION = 2
    section_charts = {}
    used_ids = set()
    placed_descs = []

    if brief_type == "full" and all_charts:
        eligible = [s for s in sections
                    if s["heading"].lower().strip() not in _NO_CHART_SECTIONS
                    and not s["heading"].strip().startswith("#")
                    and "intelligence brief" not in s["heading"].lower()]

        for sec in eligible:
            h, b = sec["heading"], sec["body"]
            remaining_budget = MAX_TOTAL - sum(len(v) for v in section_charts.values())
            if remaining_budget < 2:
                break
            candidates = [c for c in all_charts if c["id"] not in used_ids]
            per_sec_cap = min(MAX_PER_SECTION, remaining_budget)
            if per_sec_cap % 2 != 0:
                per_sec_cap -= 1
            if per_sec_cap < 2:
                break

            selected = score_charts_for_section(
                h, b, candidates, placed_descs,
                max_charts=per_sec_cap, min_score=_MIN_SCORE)

            if selected:
                section_charts[h] = selected
                for c in selected:
                    used_ids.add(c["id"])
                    placed_descs.append(c.get("description", ""))

        total_assigned = sum(len(v) for v in section_charts.values())
        log.info(f"Brief PDF: {total_assigned} charts assigned across "
                 f"{len(section_charts)} sections")

    # ── Build PDF story ────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=theme.get("name", "Brief") + " - Intelligence Brief")
    pw = A4[0] - 4.4*cm
    story = []
    emoji = theme.get("emoji", "")
    name  = theme.get("name", "Intelligence Brief")
    today = datetime.date.today().strftime("%d %B %Y")

    story.append(Paragraph(f"{emoji}  {name.upper()} - INTELLIGENCE BRIEF", SE))
    story.append(Paragraph(name, ST))
    story.append(Paragraph(
        f"Meridian Intelligence  .  {today}  .  {len(articles)} articles"
        f"  .  {len(sources)} sources", SM))
    story.append(HRFlowable(width="100%", thickness=2, color=AMBER, spaceAfter=20))

    cw = (pw - 0.5*cm) / 2

    for sec in sections:
        h, b = sec["heading"], sec["body"]
        h_clean = h.strip()

        # Skip title lines and overview
        if h_clean.startswith("#") or "intelligence brief" in h_clean.lower():
            continue
        if h_clean.lower() == "overview":
            for para in [p.strip() for p in b.split("\n\n") if p.strip()]:
                para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
                para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
                para = para.replace("&", "&amp;")
                story.append(Paragraph(para, SB))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                     color=BORD, spaceAfter=4))
            continue

        story.append(Paragraph(h_clean.upper(), SS))
        for para in [p.strip() for p in b.split("\n\n") if p.strip()]:
            para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
            para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
            para = para.replace("&", "&amp;")
            story.append(Paragraph(para, SB))

        charts_for_sec = section_charts.get(h, [])
        if charts_for_sec:
            story.append(Spacer(1, 8))
            for i in range(0, len(charts_for_sec), 2):
                pair = charts_for_sec[i:i+2]
                # Normalise both images to same height
                target_h = 7 * cm
                for c in pair:
                    ow = c["width"] or 336; oh = c["height"] or 252
                    ih = cw * (oh / ow)
                    if ih < target_h:
                        target_h = ih
                target_h = min(target_h, 7 * cm)

                cells = []
                for c in pair:
                    try:
                        ow = c["width"] or 336; oh = c["height"] or 252
                        ih = target_h
                        iw = ih * (ow / oh)
                        if iw > cw:
                            iw = cw; ih = iw * (oh / ow)
                        cells.append(RLImage(io.BytesIO(c["image_data"]),
                                             width=iw, height=ih))
                    except Exception as e:
                        log.warning(f"Chart render err: {e}")
                        cells.append(Paragraph("", SB))

                while len(cells) < 2:
                    cells.append("")

                t = Table([cells], colWidths=[cw, cw])
                t.setStyle(TableStyle([
                    ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("LEFTPADDING",   (0,0), (-1,-1), 0),
                    ("RIGHTPADDING",  (0,0), (-1,-1), 6),
                    ("TOPPADDING",    (0,0), (-1,-1), 4),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ]))
                story.append(KeepTogether(t))
            story.append(Spacer(1, 8))

        story.append(HRFlowable(width="100%", thickness=0.5, color=BORD, spaceAfter=4))

    if sources:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Sources: " + "  .  ".join(sources), SF))

    doc.build(story)
    return buf.getvalue()


_pdf_jobs = {}


def get_job(job_id):
    return _pdf_jobs.get(job_id)


def start_pdf_job(job_id, theme, articles, brief_type, db_path, base_dir,
                  pregenerated_text=None):
    """
    Start an async PDF generation job.

    If pregenerated_text is provided (text already generated by the modal
    /api/kt/brief call), skip the Sonnet API call and build the PDF directly.
    This implements the single-call architecture: generate once, use twice.
    """
    _pdf_jobs[job_id] = {"status": "running", "error": None, "ready": False}

    def _run():
        try:
            if pregenerated_text:
                # Single-call path: text was already generated for the modal
                brief_text = pregenerated_text
                log.info(f"Brief PDF {job_id}: using pre-generated text ({len(brief_text)} chars)")
            else:
                # Standalone path: generate text here (fallback / direct API use)
                cp = Path(base_dir) / "credentials.json"
                api_key = (json.loads(cp.read_text()).get("anthropic_api_key", "")
                           if cp.exists() else "")
                ctx = _build_article_context(articles, brief_type)
                name = theme.get("name", "")
                subs = theme.get("subtopics", [])
                mt = 1500 if brief_type == "short" else 4000

                prompt = _build_prompt(name, subs, ctx, brief_type)
                data = json.dumps({
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": mt,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages", data=data,
                    headers={"Content-Type": "application/json",
                             "x-api-key": api_key,
                             "anthropic-version": "2023-06-01"},
                    method="POST")
                with urllib.request.urlopen(req, timeout=180) as r:
                    brief_text = json.loads(r.read())["content"][0]["text"]

            pdf = build_brief_pdf(theme, articles, brief_text, brief_type, db_path)
            out = Path(base_dir) / f"tmp_brief_{job_id}.pdf"
            out.write_bytes(pdf)
            _pdf_jobs[job_id] = {"status": "done", "error": None, "ready": True,
                                  "path": str(out), "size": len(pdf)}
            log.info(f"Brief PDF {job_id}: done ({len(pdf)//1024}KB)")
        except Exception as e:
            log.error(f"Brief PDF {job_id}: {e}", exc_info=True)
            _pdf_jobs[job_id] = {"status": "error", "error": str(e), "ready": False}

    threading.Thread(target=_run, daemon=True).start()
