"""
Fix all four image/layout issues:
1. Maps: render at natural size (no paired scaling), bottom crop only at explicit footer line
2. Charts: reduce top crop aggression when dark region extends past y=95 (may be a legend)
3. Bottom crop: require larger white band (5+ rows) to avoid cutting content
4. PDF layout: maps get full column width, not paired height normalisation
"""
from pathlib import Path
import re

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

# ── Fix 1: Map bottom crop — only crop at explicit MAP/CHART footer ──────────
# Replace _find_bottom_crop for maps: scan upward for the specific footer text row
# The "MAP: THE ECONOMIST" line at the very bottom is dark text on white
# preceded by a white separator. We look for the LAST non-white row from the 
# bottom working upward — but only if there are 5+ consecutive white rows below it
# (the chart footer is a thick white block, not just 1-2 rows).

OLD_BOTTOM = '''def _find_bottom_crop(img):
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

    return h'''

NEW_BOTTOM = '''def _find_bottom_crop(img, is_map=False):
    """
    Crop the footer (white separator + CHART/MAP: THE ECONOMIST label).

    For charts: scan top-to-bottom in lower 40%, find first sustained
    near-white band of 5+ rows. The 5-row threshold avoids cutting at
    white regions within chart content (scale backgrounds etc).

    For maps: same logic but we also check that removing the candidate
    region doesn\'t cut into the actual map content — require 8+ white rows.
    """
    w, h = img.size
    scan_start = int(h * 0.6)
    WHITE_THRESH = 230
    MIN_RUN = 8 if is_map else 5  # maps need bigger white band to confirm footer
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

    return h'''

assert OLD_BOTTOM in src, "OLD_BOTTOM not found"
src = src.replace(OLD_BOTTOM, NEW_BOTTOM, 1)
print("fix1 bottom_crop: OK")

# ── Fix 2: Pass is_map to _find_bottom_crop in _crop_economist_chart ─────────
OLD_MAP_CROP = '''        # Maps: no top crop, no whitening — just remove footer
        if is_map:
            bottom_crop = _find_bottom_crop(img)
            log.info(f"Map crop: bottom={bottom_crop}/{h}")
            if bottom_crop < h:
                img = img.crop((0, 0, w, bottom_crop))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), img.size'''

NEW_MAP_CROP = '''        # Maps: no top crop, no whitening — just remove footer
        if is_map:
            bottom_crop = _find_bottom_crop(img, is_map=True)
            log.info(f"Map crop: bottom={bottom_crop}/{h}")
            if bottom_crop < h:
                img = img.crop((0, 0, w, bottom_crop))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), img.size'''

assert OLD_MAP_CROP in src, "OLD_MAP_CROP not found"
src = src.replace(OLD_MAP_CROP, NEW_MAP_CROP, 1)
print("fix2 map_crop: OK")

# ── Fix 3: Pass is_map to _find_bottom_crop in chart path too ────────────────
OLD_CHART_CROP = '''        # Charts: top crop + bottom crop + whiten
        top_crop = _find_top_crop(img)
        bottom_crop = _find_bottom_crop(img)'''

NEW_CHART_CROP = '''        # Charts: top crop + bottom crop + whiten
        top_crop = _find_top_crop(img)
        bottom_crop = _find_bottom_crop(img, is_map=False)'''

assert OLD_CHART_CROP in src, "OLD_CHART_CROP not found"
src = src.replace(OLD_CHART_CROP, NEW_CHART_CROP, 1)
print("fix3 chart_crop: OK")

# ── Fix 4: Top crop — be conservative when dark region extends past y=95 ─────
# If the last dark row is beyond y=95, that suggests there may be a legend
# or colour key above the chart area, not just title text. Cap the crop at
# a safer level (y=95 + 2) to avoid cutting into legitimate chart content.
OLD_TOP_RETURN = '''    if last_dark_y == 0:
        return 0

    return last_dark_y + 2'''

NEW_TOP_RETURN = '''    if last_dark_y == 0:
        return 0

    # If the last dark row extends well into the chart area (past y=95),
    # it may be a legend or colour key, not just a subtitle. Cap conservatively.
    # The bold title always ends before y=50; subtitles end before y=95.
    # Anything past y=95 that\'s still dark is likely chart content we should keep.
    if last_dark_y > 95:
        # Find the last dark row ONLY in the pure title zone (<=95)
        title_only_dark = 0
        for y in range(6, min(96, h)):
            px = _sample_row(img, y)
            if sum(1 for p in px if max(p) < 155) >= 2:
                title_only_dark = y
        if title_only_dark > 0:
            return title_only_dark + 2
        return 0  # no clear title found, don\'t crop

    return last_dark_y + 2'''

assert OLD_TOP_RETURN in src, "OLD_TOP_RETURN not found"
src = src.replace(OLD_TOP_RETURN, NEW_TOP_RETURN, 1)
print("fix4 top_crop_legend: OK")

# ── Fix 5: PDF layout — maps render at natural width, not paired scaling ──────
# In build_brief_pdf, after placing chart pairs, maps should span full column width
# The current code scales all images in a pair to the same height.
# We need to detect when an image is a map (is_map flag in processed chart dict)
# and render it full-width, not paired.
# Add is_map to the process_chart dict:
OLD_PROCESS = '''    def process_chart(c):
        fig_counter[0] += 1
        fn = fig_counter[0]
        caption = c.get("caption", "")
        processed_data, new_size = _crop_economist_chart(c["image_data"], caption)
        title = _extract_figure_title(c.get("description", ""), caption)
        nw, nh = new_size if new_size else (c.get("width") or 336, c.get("height") or 252)
        return {**c, "image_data": processed_data, "width": nw, "height": nh,
                "fig_num": fn, "fig_title": title}'''

NEW_PROCESS = '''    def process_chart(c):
        fig_counter[0] += 1
        fn = fig_counter[0]
        caption = c.get("caption", "")
        is_map_img = _is_map(caption)
        processed_data, new_size = _crop_economist_chart(c["image_data"], caption)
        title = _extract_figure_title(c.get("description", ""), caption)
        nw, nh = new_size if new_size else (c.get("width") or 336, c.get("height") or 252)
        return {**c, "image_data": processed_data, "width": nw, "height": nh,
                "fig_num": fn, "fig_title": title, "is_map": is_map_img}'''

assert OLD_PROCESS in src, "OLD_PROCESS not found"
src = src.replace(OLD_PROCESS, NEW_PROCESS, 1)
print("fix5 process_chart: OK")

# ── Fix 6: PDF render — maps get full column width, charts stay paired ────────
OLD_RENDER = '''        charts_for_sec = processed_section_charts.get(h, [])
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
                story.append(KeepTogether([t_cap, t_img]))'''

NEW_RENDER = '''        charts_for_sec = processed_section_charts.get(h, [])
        if charts_for_sec:
            story.append(Spacer(1, 6))
            for i in range(0, len(charts_for_sec), 2):
                pair = charts_for_sec[i:i+2]

                # Maps render at full page width (pw), not paired half-width (cw)
                # Charts render as pairs at half-width
                any_map = any(c.get("is_map") for c in pair)

                if any_map:
                    # Render each map individually at full width
                    for c in pair:
                        try:
                            ow = c["width"] or 336; oh = c["height"] or 252
                            # Scale to full page width, cap height at 10cm
                            iw = pw
                            ih = iw * (oh / ow)
                            if ih > 10 * cm:
                                ih = 10 * cm; iw = ih * (ow / oh)
                            cap_para = Paragraph(
                                f"Figure {c['fig_num']} — {c['fig_title']}", SFIG)
                            img_elem = RLImage(io.BytesIO(c["image_data"]),
                                              width=iw, height=ih)
                            story.append(KeepTogether([cap_para, img_elem,
                                                       Spacer(1, 8)]))
                        except Exception as e:
                            log.warning(f"Map render err: {e}")
                else:
                    # Regular paired chart rendering
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
                    story.append(KeepTogether([t_cap, t_img]))'''

assert OLD_RENDER in src, "OLD_RENDER not found"
src = src.replace(OLD_RENDER, NEW_RENDER, 1)
print("fix6 map_fullwidth: OK")

p.write_text(src)
print("Written OK")
