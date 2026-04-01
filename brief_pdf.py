"""
brief_pdf.py - Intelligence Brief PDF generation for Meridian.
"""
import io, re, sqlite3, logging, threading, datetime, urllib.request, json
from pathlib import Path

log = logging.getLogger("meridian")

_NO_CHART_SECTIONS = {
    "executive summary", "cross-cutting themes", "source notes",
    "strategic implications", "watch list", "key developments", "overview"
}
_MIN_SCORE = 2
_CROSS_BRIEF_SIMILARITY = 0.5
_ECON_BG_RGB = (236, 235, 223)
_BG_TOLERANCE = 18


def _tok(text):
    return set(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())


def _desc_similar(a, b, threshold=0.6):
    ta, tb = _tok(a), _tok(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / max(len(ta), len(tb)) > threshold


def _dedup_by_description(charts):
    kept = []
    for c in charts:
        desc = c.get("description", "")
        if not any(_desc_similar(desc, k.get("description", "")) for k in kept):
            kept.append(c)
    return kept


def _is_map(caption):
    return "map:" in (caption or "").lower()


def _whiten_background(img):
    """Replace Economist beige background with white using numpy."""
    try:
        import numpy as np
        arr = np.array(img, dtype=np.int16)
        r_bg, g_bg, b_bg = _ECON_BG_RGB
        tol = _BG_TOLERANCE
        mask = (
            (np.abs(arr[:, :, 0] - r_bg) <= tol) &
            (np.abs(arr[:, :, 1] - g_bg) <= tol) &
            (np.abs(arr[:, :, 2] - b_bg) <= tol)
        )
        arr[mask] = [255, 255, 255]
        from PIL import Image
        return Image.fromarray(arr.astype(np.uint8))
    except Exception as e:
        log.warning(f"Whiten failed: {e}")
        return img


def _sample_row(img, y, step=None):
    w = img.size[0]
    step = step or max(1, w // 26)
    return [img.getpixel((x, y)) for x in range(4, w - 4, step)]


def _row_is_white(px):
    return sum(1 for p in px if min(p) > 245) >= len(px) * 0.9


def _row_is_beige(px):
    r_bg, g_bg, b_bg = _ECON_BG_RGB
    tol = 22
    return sum(1 for p in px
               if abs(p[0]-r_bg) <= tol
               and abs(p[1]-g_bg) <= tol
               and abs(p[2]-b_bg) <= tol) >= len(px) * 0.75


def _row_dark_count(px):
    return sum(1 for p in px if max(p) < 130)


def _find_top_crop(img):
    """
    Crop the entire title block: bold title + subtitle line(s).

    Strategy: scan only the fixed title region (y=6 to y=95 — the Economist
    title block never extends beyond ~90px). Find the LAST dark text row in
    that region. Crop at last_dark + 2.

    This is simpler and more reliable than hunting for a beige run gap:
    - Capping at y=95 means we never accidentally pick up chart data rows
    - last_dark + 2 gives one pixel of padding after the title block ends
    - Works for both single-subtitle and double-subtitle charts
    - Maps skip this function entirely (handled by caller)
    """
    w, h = img.size
    # Scan to y=110: some 3-line subtitle blocks extend to y=83+
    # Use threshold 155 (not 130) to catch medium-grey italic subtitle text
    TITLE_REGION_END = min(110, h // 4)

    last_dark_y = 0
    for y in range(6, TITLE_REGION_END):
        px = _sample_row(img, y)
        if sum(1 for p in px if max(p) < 155) >= 2:
            last_dark_y = y

    if last_dark_y == 0:
        return 0

    return last_dark_y + 2


def _find_bottom_crop(img):
    """
    Crop at the beige-to-white boundary — removing white separator and footer.
    Scans top-to-bottom in lower 40% for first sustained near-white band.
    """
    w, h = img.size
    scan_start = int(h * 0.6)
    WHITE_THRESH = 230
    MIN_RUN = 3
    white_run_start = None
    white_run = 0

    for y in range(scan_start, h):
        px = _sample_row(img, y)
        near_white = sum(1 for p in px if min(p) > WHITE_THRESH)
        if near_white >= len(px) * 0.85:
            if white_run == 0:
                white_run_start = y
            white_run += 1
            if white_run >= MIN_RUN:
                return white_run_start
        else:
            white_run = 0
            white_run_start = None

    return h


def _is_double_image(img):
    """Detect two stacked Economist figures captured as one screenshot."""
    w, h = img.size
    step = max(1, w // 20)
    for y in range(h // 3, h * 2 // 3):
        very_dark = sum(1 for x in range(4, w - 4, step)
                        if img.getpixel((x, y))[0] < 30)
        if very_dark >= (w // step) * 0.6:
            return True
    return False


def _crop_economist_chart(image_data, caption=""):
    """
    Process an Economist chart/map image.
    - Maps: bottom crop only (remove CHART/MAP: THE ECONOMIST footer), no whitening.
    - Charts: top crop (remove title+subtitle) + bottom crop + whiten background.
    - Double images: bottom crop only, no whitening.
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        w, h = img.size
        is_map = _is_map(caption)

        # Double image detection (two figures stacked)
        if _is_double_image(img):
            log.info(f"Double image ({w}x{h}), skipping top crop")
            bottom_crop = _find_bottom_crop(img)
            if bottom_crop < h:
                img = img.crop((0, 0, w, bottom_crop))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), img.size

        # Maps: no top crop, no whitening — just remove footer
        if is_map:
            bottom_crop = _find_bottom_crop(img)
            log.info(f"Map crop: bottom={bottom_crop}/{h}")
            if bottom_crop < h:
                img = img.crop((0, 0, w, bottom_crop))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), img.size

        # Charts: top crop + bottom crop + whiten
        top_crop = _find_top_crop(img)
        bottom_crop = _find_bottom_crop(img)

        log.info(f"Chart crop: top={top_crop} bottom={bottom_crop}/{h}")

        if top_crop > 0 or bottom_crop < h:
            top_crop = max(0, top_crop)
            bottom_crop = min(h, bottom_crop)
            if bottom_crop > top_crop + 30:
                img = img.crop((0, top_crop, w, bottom_crop))

        img = _whiten_background(img)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), img.size

    except Exception as e:
        log.warning(f"Chart processing failed: {e}")
        return image_data, None


def _extract_figure_title(description, caption):
    """Derive a clean short figure title from the Haiku description."""
    desc = (description or "").strip()
    desc = re.sub(r"^#+\s*", "", desc)
    if not desc:
        return "Map" if "map" in (caption or "").lower() else "Chart"

    # Strip generic openers like "The chart shows..." to get to the subject
    desc = re.sub(r"^(The chart|This chart|The graph|This graph|The map|This map)"
                  r"\s+(shows?|depicts?|displays?|illustrates?|indicates?)\s+",
                  "", desc, flags=re.IGNORECASE)

    # Take first clause up to comma or period
    for sep in [",", ".", ";"]:
        if sep in desc:
            title = desc.split(sep)[0].strip()
            break
    else:
        title = desc

    # Strip trailing interpretive verb phrases
    title = re.sub(
        r"\s+(surged?|fell|drops?|rose|declined?|increased?|decreased?|"
        r"shows?|reveals?|indicates?|demonstrates?|peaked?|spiked?|has\s)\b.*",
        "", title, flags=re.IGNORECASE)

    # If still too generic, use first 2 clauses
    if len(title) < 10 or title.lower() in ("the chart", "the graph", "the map"):
        parts = re.split(r"[,.]", desc)
        title = " — ".join(p.strip() for p in parts[:2] if p.strip())

    if len(title) > 72:
        title = title[:72].rsplit(" ", 1)[0]
    return title.rstrip(".,;") if title else "Figure"


def score_charts_for_section(section_heading, section_text, charts,
                              placed_descriptions, max_charts=2,
                              min_score=_MIN_SCORE):
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
    if len(result) == 1:
        return []
    return result


def _build_prompt(theme_name, subtopics, article_context, brief_type):
    SECTION_INSTRUCTION = (
        "[2-3 paragraphs of analytical prose. "
        "Lead each paragraph with the key analytical finding. "
        "Support findings with specific figures, percentages, prices, quantities "
        "or dates from the source articles where available. "
        "Close with the forward-looking implication. "
        "Only cite statistics that appear in the articles provided.]"
    )
    if brief_type == "short":
        return (
            f'You are a senior intelligence analyst. '
            f'Write a concise intelligence brief on "{theme_name}".\n\n'
            f"Where source articles contain specific figures, percentages, prices or data points, "
            f"incorporate them precisely. Do not invent statistics.\n\n"
            f"Structure:\n"
            f"## Executive Summary\n[2-3 sentences]\n\n"
            f"## Key Developments\n[5-7 bullet points with figures/dates where available]\n\n"
            f"## Strategic Implications\n{SECTION_INSTRUCTION}\n\n"
            f"## Watch List\n[3-5 specific items]\n\n"
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
            f"quantities or dates, incorporate them precisely — "
            f"one or two per section to anchor the assessment. "
            f"Do not invent or estimate statistics.\n\n"
            f"Structure:\n"
            f"## Executive Summary\n[3-4 sentences.]\n\n"
            + subtopic_sections + "\n\n"
            f"## Cross-cutting Themes\n[3-4 patterns across subtopics]\n\n"
            f"## Strategic Implications\n[2-3 paragraphs forward-looking]\n\n"
            f"ARTICLES:\n{article_context}"
        )


def _build_article_context(articles, brief_type):
    MAX_ARTICLES = 30 if brief_type == "short" else 60
    BODY_EXCERPT = 400
    parts = []
    for a in articles[:MAX_ARTICLES]:
        if not a.get("summary"):
            continue
        snippet = f"SOURCE: {a.get('source', '')}\nTITLE: {a.get('title', '')}\n"
        snippet += f"SUMMARY: {a.get('summary', '')}"
        body = (a.get("body") or "").strip()
        if body and len(body) > 100:
            excerpt = body[:BODY_EXCERPT].rsplit(" ", 1)[0]
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
    DARK = HexColor("#1a1a1a"); BORD = HexColor("#ddd8cc"); FIGC = HexColor("#555555")

    def S(name, **kw):
        d = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=DARK,
                 spaceAfter=0, spaceBefore=0)
        d.update(kw); return ParagraphStyle(name, **d)

    SE   = S("e", fontSize=7,  textColor=AMBER, fontName="Helvetica-Bold",
             letterSpacing=1.5, spaceAfter=4)
    ST   = S("t", fontSize=22, fontName="Helvetica-Bold", leading=26, spaceAfter=6)
    SM   = S("m", fontSize=8,  textColor=LIGHT, spaceAfter=16)
    SS   = S("s", fontSize=8,  textColor=AMBER, fontName="Helvetica-Bold",
             letterSpacing=1.2, spaceAfter=8, spaceBefore=20)
    SB   = S("b", fontSize=10, leading=16, textColor=MID, spaceAfter=10,
             alignment=4)  # JUSTIFY
    SF   = S("f", fontSize=7,  textColor=LIGHT, letterSpacing=0.8)
    SFIG = S("fig", fontSize=8, textColor=FIGC, fontName="Helvetica-Oblique",
             leading=11, spaceAfter=4, spaceBefore=8)

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
            remaining = MAX_TOTAL - sum(len(v) for v in section_charts.values())
            if remaining < 2:
                break
            candidates = [c for c in all_charts if c["id"] not in used_ids]
            cap = min(MAX_PER_SECTION, remaining)
            if cap % 2 != 0:
                cap -= 1
            if cap < 2:
                break
            selected = score_charts_for_section(
                h, b, candidates, placed_descs, max_charts=cap)
            if selected:
                section_charts[h] = selected
                for c in selected:
                    used_ids.add(c["id"])
                    placed_descs.append(c.get("description", ""))

        log.info(f"Brief PDF: {sum(len(v) for v in section_charts.values())} charts "
                 f"across {len(section_charts)} sections")

    fig_counter = [0]

    def process_chart(c):
        fig_counter[0] += 1
        fn = fig_counter[0]
        caption = c.get("caption", "")
        processed_data, new_size = _crop_economist_chart(c["image_data"], caption)
        title = _extract_figure_title(c.get("description", ""), caption)
        nw, nh = new_size if new_size else (c.get("width") or 336, c.get("height") or 252)
        return {**c, "image_data": processed_data, "width": nw, "height": nh,
                "fig_num": fn, "fig_title": title}

    processed_section_charts = {
        h: [process_chart(c) for c in charts]
        for h, charts in section_charts.items()
    }

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
        if h_clean.startswith("#") or "intelligence brief" in h_clean.lower():
            continue
        if h_clean.lower() == "overview":
            for para in [p.strip() for p in b.split("\n\n") if p.strip()]:
                para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
                para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
                para = para.replace("&", "&amp;")
                story.append(Paragraph(para, SB))
            story.append(HRFlowable(width="100%", thickness=0.5, color=BORD, spaceAfter=4))
            continue

        story.append(Paragraph(h_clean.upper(), SS))
        for para in [p.strip() for p in b.split("\n\n") if p.strip()]:
            para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
            para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
            para = para.replace("&", "&amp;")
            story.append(Paragraph(para, SB))

        charts_for_sec = processed_section_charts.get(h, [])
        if charts_for_sec:
            story.append(Spacer(1, 6))
            for i in range(0, len(charts_for_sec), 2):
                pair = charts_for_sec[i:i+2]
                # Use consistent height scaled to column width
                target_h = 7 * cm
                for c in pair:
                    ow = c["width"] or 336; oh = c["height"] or 252
                    ih = cw * (oh / ow)
                    if ih < target_h:
                        target_h = ih
                target_h = min(target_h, 7 * cm)

                img_cells, cap_cells = [], []
                for c in pair:
                    try:
                        ow = c["width"] or 336; oh = c["height"] or 252
                        ih = target_h
                        iw = ih * (ow / oh)
                        if iw > cw:
                            iw = cw; ih = iw * (oh / ow)
                        img_cells.append(RLImage(io.BytesIO(c["image_data"]),
                                                 width=iw, height=ih))
                        cap_cells.append(Paragraph(
                            f"Figure {c['fig_num']} — {c['fig_title']}", SFIG))
                    except Exception as e:
                        log.warning(f"Chart render err: {e}")
                        img_cells.append(Paragraph("", SB))
                        cap_cells.append(Paragraph("", SFIG))

                while len(img_cells) < 2:
                    img_cells.append(""); cap_cells.append("")

                t_cap = Table([cap_cells], colWidths=[cw, cw])
                t_cap.setStyle(TableStyle([
                    ("ALIGN",         (0,0), (-1,-1), "LEFT"),
                    ("VALIGN",        (0,0), (-1,-1), "TOP"),
                    ("LEFTPADDING",   (0,0), (-1,-1), 4),
                    ("RIGHTPADDING",  (0,0), (-1,-1), 6),
                    ("TOPPADDING",    (0,0), (-1,-1), 0),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                ]))
                t_img = Table([img_cells], colWidths=[cw, cw])
                t_img.setStyle(TableStyle([
                    ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("LEFTPADDING",   (0,0), (-1,-1), 0),
                    ("RIGHTPADDING",  (0,0), (-1,-1), 6),
                    ("TOPPADDING",    (0,0), (-1,-1), 0),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                ]))
                story.append(KeepTogether([t_cap, t_img]))

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
    _pdf_jobs[job_id] = {"status": "running", "error": None, "ready": False}

    def _run():
        try:
            if pregenerated_text:
                brief_text = pregenerated_text
                log.info(f"Brief PDF {job_id}: using pre-generated text")
            else:
                cp = Path(base_dir) / "credentials.json"
                api_key = (json.loads(cp.read_text()).get("anthropic_api_key", "")
                           if cp.exists() else "")
                ctx = _build_article_context(articles, brief_type)
                prompt = _build_prompt(theme.get("name", ""), theme.get("subtopics", []),
                                       ctx, brief_type)
                mt = 1500 if brief_type == "short" else 4000
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
