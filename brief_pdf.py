"""
brief_pdf.py - Intelligence Brief PDF generation for Meridian.
"""
import io, re, sqlite3, logging, threading, datetime, urllib.request, json
from pathlib import Path

log = logging.getLogger("meridian")

# Headings that should never receive charts
_NO_CHART_SECTIONS = {"executive summary", "cross-cutting themes", "source notes",
                      "strategic implications", "watch list", "key developments"}

# Minimum keyword-overlap score for a chart to qualify for a section
_MIN_SCORE = 2

def _tok(text):
    return set(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())

def _desc_similar(a, b):
    """True if two description strings share >60% of tokens — i.e. same chart."""
    ta, tb = _tok(a), _tok(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / max(len(ta), len(tb)) > 0.6

def _dedup_by_description(charts):
    """Remove near-duplicate images (same chart pushed twice).
    Keeps the first occurrence of each visually-similar image."""
    kept = []
    for c in charts:
        desc = c.get("description", "")
        if not any(_desc_similar(desc, k.get("description", "")) for k in kept):
            kept.append(c)
    return kept

def score_charts_for_section(section_heading, section_text, charts,
                              max_charts=2, min_score=_MIN_SCORE):
    """Score candidate charts against a section and return the top matches.

    Changes vs original:
    - Executive Summary and other prose-only sections return [] immediately
    - Minimum score threshold (default 2) — loose single-word overlap excluded
    - max_charts defaults to 2 (caller may pass 1 for budget management)
    - Deduplication by article_id still applies
    """
    if section_heading.lower().strip() in _NO_CHART_SECTIONS:
        return []
    section_tokens = _tok(section_heading + " " + section_text)
    if not section_tokens:
        return []
    scored = []
    for c in charts:
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
    return result


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

    # ── Fetch candidate charts from DB ────────────────────────────────────────
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

    # Remove near-duplicate images (same chart pushed twice due to legacy rows)
    all_charts = _dedup_by_description(all_charts)
    log.info(f"Brief PDF: {len(all_charts)} distinct charts for {len(article_ids)} articles")

    # ── Parse brief text into sections ───────────────────────────────────────
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

    # ── Pre-assign charts to sections (one pass) ─────────────────────────────
    # Strategy: skip no-chart sections, then give each eligible section
    # up to 1 chart by default, up to 2 if score is strong (>=4).
    # Global cap = 14 (2 per section * 7 subtopics) but effectively limited
    # by the distinct charts available.
    MAX_TOTAL = 14
    MAX_PER_SECTION = 2
    section_charts = {}   # heading -> [chart, ...]
    used_ids = set()

    if brief_type == "full" and all_charts:
        eligible = [s for s in sections
                    if s["heading"].lower().strip() not in _NO_CHART_SECTIONS]
        n_eligible = len(eligible)

        for sec in eligible:
            h, b = sec["heading"], sec["body"]
            remaining_budget = MAX_TOTAL - sum(len(v) for v in section_charts.values())
            if remaining_budget <= 0:
                break
            remaining_sections = n_eligible - len(section_charts)
            # Allow up to 2 per section; but if budget is tight, limit to 1
            per_sec_cap = min(MAX_PER_SECTION,
                              max(1, remaining_budget // max(remaining_sections, 1)))
            candidates = [c for c in all_charts if c["id"] not in used_ids]
            selected = score_charts_for_section(h, b, candidates,
                                                max_charts=per_sec_cap,
                                                min_score=_MIN_SCORE)
            if selected:
                section_charts[h] = selected
                for c in selected:
                    used_ids.add(c["id"])

        total_assigned = sum(len(v) for v in section_charts.values())
        log.info(f"Brief PDF: {total_assigned} charts assigned across "
                 f"{len(section_charts)} sections")

    # ── Build PDF story ───────────────────────────────────────────────────────
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

    cw = (pw - 0.5*cm) / 2   # column width for 2-per-row chart layout

    for sec in sections:
        h, b = sec["heading"], sec["body"]
        story.append(Paragraph(h.upper(), SS))
        for para in [p.strip() for p in b.split("\n\n") if p.strip()]:
            para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
            para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
            para = para.replace("&", "&amp;")
            story.append(Paragraph(para, SB))

        charts_for_sec = section_charts.get(h, [])
        if charts_for_sec:
            story.append(Spacer(1, 8))
            for i in range(0, len(charts_for_sec), 2):
                pair  = charts_for_sec[i:i+2]
                cells = []
                for c in pair:
                    try:
                        ow = c["width"]  or 336
                        oh = c["height"] or 252
                        # Fix: cap width first so the image fills the column
                        # then only height-cap if the result is still too tall.
                        # This preserves the top of maps/charts (where titles live).
                        iw = cw
                        ih = iw * (oh / ow)
                        if ih > 7*cm:
                            ih = 7*cm
                            iw = ih * (ow / oh)
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


def start_pdf_job(job_id, theme, articles, brief_type, db_path, base_dir):
    _pdf_jobs[job_id] = {"status": "running", "error": None, "ready": False}
    def _run():
        try:
            cp = Path(base_dir) / "credentials.json"
            api_key = (json.loads(cp.read_text()).get("anthropic_api_key", "")
                       if cp.exists() else "")
            ctx = "\n\n---\n\n".join(
                "SOURCE: " + a.get("source", "") + "\nTITLE: " + a.get("title", "")
                + "\nSUMMARY: " + a.get("summary", "")
                for a in articles if a.get("summary"))
            name = theme.get("name", "")
            em   = theme.get("emoji", "")
            subs = theme.get("subtopics", [])
            if brief_type == "short":
                prompt = (
                    f'You are a senior intelligence analyst. Write a concise intelligence brief on "{name}".\n\n'
                    "Structure:\n## Executive Summary\n[2-3 sentences]\n\n"
                    "## Key Developments\n[5-7 bullets]\n\n"
                    f"## Strategic Implications\n[2-3 paragraphs]\n\n"
                    f"## Watch List\n[3-5 items]\n\nARTICLES:\n{ctx}"
                )
                mt = 1500
            else:
                ss = "\n\n".join(
                    f"## {s}\n[2-3 paragraphs of analytical prose]" for s in subs)
                prompt = (
                    f'You are a senior intelligence analyst. Write a comprehensive intelligence brief on "{name}".\n\n'
                    f"Structure:\n## {em} {name} - Intelligence Brief\n\n"
                    f"## Executive Summary\n[3-4 sentences]\n\n"
                    + ss + "\n\n## Cross-cutting Themes\n[overarching patterns]\n\n"
                    f"## Strategic Implications\n[forward-looking analysis]\n\n"
                    f"ARTICLES:\n{ctx}"
                )
                mt = 4000
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
