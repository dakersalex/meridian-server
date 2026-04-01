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

# Economist chart background colour (warm grey-beige) and replacement tolerance
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
    """True if this image is a map (not a chart). Maps skip background whitening."""
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
    except ImportError:
        return img


def _find_top_crop(img):
    """
    Find where the Economist title block ends and chart data begins.
    Scans from top, looking for:
      - The red accent bar (very red pixels near top)
      - Then bold title text rows
      - Then a clear gap of background-coloured rows
    Returns the y pixel to crop from (0 = no crop needed).

    Key insight: we must do this BEFORE whitening the background,
    because whitening turns the beige background rows white and makes
    them indistinguishable from the clear gap we're scanning for.
    """
    from PIL import Image
    w, h = img.size

    # Sample row average using original image colours
    def row_avg(y):
        return sum(img.getpixel((x, y))[0] for x in range(0, w, max(1, w // 20))) // max(1, w // 20)

    def row_has_red_bar(y):
        """Detect the Economist's thin red accent bar near the top."""
        reds = sum(1 for x in range(0, w, max(1, w // 20))
                   if img.getpixel((x, y))[0] > 150
                   and img.getpixel((x, y))[1] < 80
                   and img.getpixel((x, y))[2] < 80)
        return reds >= 3

    # Step 1: find the red bar (should be within first 20px)
    red_bar_y = None
    for y in range(0, min(25, h)):
        if row_has_red_bar(y):
            red_bar_y = y
            break

    if red_bar_y is None:
        # No red bar found — might be a map or unusual chart. Don't crop top.
        return 0

    # Step 2: find end of title block
    # The title block consists of:
    #   - red bar (1-2px)
    #   - bold title (~20px, dark text on beige)
    #   - subtitle (~14px, dark text on beige)
    #   - a clear beige gap (~8-12px)
    # We scan from just after the red bar looking for a sustained
    # background-coloured (beige) region that follows some text rows.
    # "Text row" = average brightness < 220 (darker than plain beige)
    # "Beige row" = average within 20 of beige background

    r_bg, g_bg, b_bg = _ECON_BG_RGB
    tol = 22  # slightly looser for scan purposes

    def is_beige_row(y):
        samples = [img.getpixel((x, y)) for x in range(0, w, max(1, w // 20))]
        beige_count = sum(1 for p in samples
                          if abs(p[0] - r_bg) <= tol
                          and abs(p[1] - g_bg) <= tol
                          and abs(p[2] - b_bg) <= tol)
        return beige_count >= len(samples) * 0.7  # 70% beige = clear row

    # Find last text row in title region (scan 10-100px)
    last_text_y = red_bar_y
    title_scan_end = min(110, h)
    for y in range(red_bar_y + 2, title_scan_end):
        avg = row_avg(y)
        if avg < 210:  # has some dark content = text
            last_text_y = y

    # Now find first sustained beige gap AFTER last_text_y
    MIN_BEIGE_RUN = 5
    beige_run = 0
    crop_y = 0
    for y in range(last_text_y + 1, min(last_text_y + 30, h)):
        if is_beige_row(y):
            beige_run += 1
            if beige_run >= MIN_BEIGE_RUN:
                crop_y = y - beige_run + 1
                break
        else:
            beige_run = 0

    # Sanity check: don't crop more than 15% of image height
    max_crop = int(h * 0.15)
    if crop_y > max_crop:
        log.warning(f"Top crop {crop_y} exceeds 15% of height {h}, capping at {max_crop}")
        crop_y = max_crop

    return crop_y


def _find_bottom_crop(img):
    """
    Find where the footer label starts ("CHART: THE ECONOMIST" / "MAP: THE ECONOMIST").
    Scans upward from bottom looking for the white separator line.
    Returns the y pixel to crop to (h = no crop needed).
    """
    w, h = img.size
    WHITE_THRESH = 245
    MIN_WHITE_RUN = 3
    bottom_crop = h
    white_run = 0
    for y in range(h - 1, max(h - 80, 0), -1):
        row_avg = sum(img.getpixel((x, y))[0]
                      for x in range(0, w, max(1, w // 20))) // max(1, w // 20)
        if row_avg >= WHITE_THRESH:
            white_run += 1
            if white_run >= MIN_WHITE_RUN:
                bottom_crop = y - white_run + 1
                for y2 in range(y - white_run, max(h - 80, 0), -1):
                    row_avg2 = sum(img.getpixel((x2, y2))[0]
                                   for x2 in range(0, w, max(1, w // 20))) // max(1, w // 20)
                    if row_avg2 >= WHITE_THRESH:
                        bottom_crop = y2
                    else:
                        break
                break
        else:
            white_run = 0
    return bottom_crop


def _is_double_image(img):
    """
    Detect if this image contains two stacked Economist figures captured together.
    Signature: a wide very-dark horizontal band (separator / image boundary)
    in the middle third of the image.
    Returns True if detected (image should be used as-is / skipped from processing).
    """
    w, h = img.size
    # Scan middle third for a near-black horizontal band
    for y in range(h // 3, h * 2 // 3):
        dark_count = sum(1 for x in range(0, w, max(1, w // 20))
                         if img.getpixel((x, y))[0] < 30)
        if dark_count >= (w // 20) * 0.6:  # 60% of sampled pixels very dark
            return True
    return False


def _crop_economist_chart(image_data, caption=""):
    """
    Process an Economist chart/map image:
    1. Detect if it's a double-captured image (two figures stacked) — if so, skip cropping.
    2. Crop the top title band BEFORE whitening (so beige rows are still detectable).
    3. Crop the bottom "CHART/MAP: THE ECONOMIST" label.
    4. For charts only (not maps): whiten the beige background.
    Returns: (processed_bytes, new_size)
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        w, h = img.size
        is_map = _is_map(caption)

        # Detect double-captured images — don't crop, just remove footer
        if _is_double_image(img):
            log.info(f"Double image detected ({w}x{h}), skipping top crop")
            bottom_crop = _find_bottom_crop(img)
            if bottom_crop < h:
                img = img.crop((0, 0, w, bottom_crop))
            # No whitening for double images (likely contains maps/photos)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), img.size

        # Step 1: find crop points BEFORE whitening
        top_crop = _find_top_crop(img)
        bottom_crop = _find_bottom_crop(img)

        # Step 2: apply crops
        if top_crop > 0 or bottom_crop < h:
            top_crop = max(0, top_crop)
            bottom_crop = min(h, bottom_crop)
            if bottom_crop > top_crop + 20:
                img = img.crop((0, top_crop, w, bottom_crop))

        # Step 3: whiten background for charts only (maps keep original colours)
        if not is_map:
            img = _whiten_background(img)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), img.size

    except Exception as e:
        log.warning(f"Chart processing failed: {e}")
        return image_data, None


def _extract_figure_title(description, caption):
    """
    Derive a clean figure title from the Haiku description.
    Uses the first factual clause — strips interpretive language
    like 'surged dramatically' in favour of the plain subject.
    """
    desc = (description or "").strip()
    # Strip any markdown headers Haiku may have produced
    desc = re.sub(r"^#+\s*", "", desc)
    if not desc:
        return "Map" if "map" in (caption or "").lower() else "Chart"

    # Take first clause up to first comma, period, semicolon or verb phrase
    for sep in [",", ".", ";"]:
        if sep in desc:
            title = desc.split(sep)[0].strip()
            break
    else:
        title = desc

    # Remove interpretive tail phrases (e.g. "...surged dramatically following X")
    # by capping at the first verb indicator after a noun phrase
    title = re.sub(r"\s+(surged|fell|rose|declined|increased|decreased|shows?|"
                   r"reveals?|indicates?|demonstrates?|peaked?|dropped?)\b.*", "",
                   title, flags=re.IGNORECASE)

    if len(title) > 70:
        title = title[:70].rsplit(" ", 1)[0]

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


def _build_prompt(theme_name, subtopics, article_context, brief_type,
                  figure_index=None):
    SECTION_INSTRUCTION = (
        "[2-3 paragraphs of analytical prose. "
        "Lead each paragraph with the key analytical finding. "
        "Support findings with specific figures, percentages, prices, quantities "
        "or dates from the source articles where available — these anchor the analysis. "
        "Close with the forward-looking implication. "
        "Only cite statistics that appear in the articles provided.]"
    )
    figure_guidance = ""
    if figure_index:
        fig_lines = "\n".join(
            f"  Figure {fn}: {ft} (appears in section: {fs})"
            for fn, ft, fs in figure_index
        )
        figure_guidance = (
            f"\nThe following charts will appear in the PDF. "
            f"Where relevant, reference them by figure number:\n{fig_lines}\n"
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
            f"Do not invent or estimate statistics; only use figures present in the articles."
            f"{figure_guidance}\n\n"
            f"Structure:\n"
            f"## Executive Summary\n"
            f"[3-4 sentences. State the overarching assessment directly.]\n\n"
            + subtopic_sections + "\n\n"
            f"## Cross-cutting Themes\n"
            f"[3-4 analytical observations that cut across the subtopics above]\n\n"
            f"## Strategic Implications\n"
            f"[2-3 paragraphs of forward-looking analysis.]\n\n"
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
    DARK = HexColor("#1a1a1a"); BORD = HexColor("#ddd8cc"); FIGC = HexColor("#444444")

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
    SB   = S("b", fontSize=10, leading=16, textColor=MID, spaceAfter=10)
    SF   = S("f", fontSize=7,  textColor=LIGHT, letterSpacing=0.8)
    # Figure caption: italic grey, sits ABOVE the image
    SFIG = S("fig", fontSize=8, textColor=FIGC, fontName="Helvetica-Oblique",
             leading=11, spaceAfter=4, spaceBefore=8)

    # ── Fetch charts ───────────────────────────────────────────────────────────
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

    # ── Process images: crop then whiten, assign figure numbers ───────────────
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

    processed_section_charts = {}
    for h, charts in section_charts.items():
        processed_section_charts[h] = [process_chart(c) for c in charts]

    # ── Build PDF ──────────────────────────────────────────────────────────────
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

                # Normalise pair to same height
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

                # Caption ABOVE image — render caption row first, then image row
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
                log.info(f"Brief PDF {job_id}: using pre-generated text ({len(brief_text)} chars)")
            else:
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
