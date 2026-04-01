"""
Patch brief_pdf.py layout:
1. Reduce chart height from 7cm to 5cm - less dominant on page
2. Single chart/map: text wraps alongside (2-col table, text left, image right)
3. Two charts: side by side as before (already working well per feedback)  
4. Maps: cap at natural size, don't upscale beyond original pixels
5. Charts placed INLINE with section text, not dumped after all text
"""
from pathlib import Path

p = Path('/Users/alexdakers/meridian-server/brief_pdf.py')
src = p.read_text()

# ── Fix 1: Reduce paired chart height cap from 7cm to 5cm ────────────────────
OLD_H = "                    target_h = 7 * cm\n                    for c in pair:\n                        ow = c[\"width\"] or 336; oh = c[\"height\"] or 252\n                        ih = cw * (oh / ow)\n                        if ih < target_h:\n                            target_h = ih\n                    target_h = min(target_h, 7 * cm)"

NEW_H = "                    target_h = 5 * cm\n                    for c in pair:\n                        ow = c[\"width\"] or 336; oh = c[\"height\"] or 252\n                        ih = cw * (oh / ow)\n                        if ih < target_h:\n                            target_h = ih\n                    target_h = min(target_h, 5 * cm)"

assert OLD_H in src, "OLD_H not found"
src = src.replace(OLD_H, NEW_H, 1)
print("fix1 height: OK")

# ── Fix 2: Maps cap at natural rendered size, not full page width ─────────────
# A 336px-wide image at 72dpi = 336/72 * 2.54cm ≈ 11.9cm natural size
# Upscaling to pw=16.6cm makes it blurry. Cap at natural size or half page.
OLD_MAP = """                if any_map:
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
                            log.warning(f"Map render err: {e}")"""

NEW_MAP = """                if any_map:
                    # Maps: render side by side with text if section has text,
                    # or at natural size (not upscaled). Natural size for a
                    # 336px image: 336px / 96dpi * 2.54 = ~8.9cm.
                    # Cap at half page width so two maps can sit side by side.
                    MAP_MAX_W = pw / 2 - 0.3 * cm  # half page minus gap
                    MAP_MAX_H = 9 * cm

                    # Collect all map image elements for this pair
                    map_cap_cells, map_img_cells = [], []
                    for c in pair:
                        try:
                            ow = c["width"] or 336; oh = c["height"] or 252
                            # Scale to natural pixel size (96dpi equivalent)
                            nat_w = ow / 96 * 2.54 * cm  # cm
                            nat_h = nat_w * (oh / ow)
                            # Cap at max dimensions
                            iw = min(nat_w, MAP_MAX_W)
                            ih = iw * (oh / ow)
                            if ih > MAP_MAX_H:
                                ih = MAP_MAX_H; iw = ih * (ow / oh)
                            map_img_cells.append(RLImage(io.BytesIO(c["image_data"]),
                                                         width=iw, height=ih))
                            map_cap_cells.append(Paragraph(
                                f"Figure {c['fig_num']} — {c['fig_title']}", SFIG))
                        except Exception as e:
                            log.warning(f"Map render err: {e}")
                            map_img_cells.append(Paragraph("", SB))
                            map_cap_cells.append(Paragraph("", SFIG))

                    while len(map_img_cells) < 2:
                        map_img_cells.append(""); map_cap_cells.append("")

                    # Render as a pair (same as charts) so they sit side by side
                    t_cap = Table([map_cap_cells], colWidths=[cw, cw])
                    t_cap.setStyle(TableStyle([
                        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
                        ("VALIGN",        (0,0), (-1,-1), "TOP"),
                        ("LEFTPADDING",   (0,0), (-1,-1), 4),
                        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
                        ("TOPPADDING",    (0,0), (-1,-1), 0),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                    ]))
                    t_img = Table([map_img_cells], colWidths=[cw, cw])
                    t_img.setStyle(TableStyle([
                        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                        ("VALIGN",        (0,0), (-1,-1), "TOP"),
                        ("LEFTPADDING",   (0,0), (-1,-1), 0),
                        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
                        ("TOPPADDING",    (0,0), (-1,-1), 0),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                    ]))
                    story.append(KeepTogether([t_cap, t_img]))"""

assert OLD_MAP in src, "OLD_MAP not found"
src = src.replace(OLD_MAP, NEW_MAP, 1)
print("fix2 map_size: OK")

# ── Fix 3: Restructure section rendering: charts inline with text ─────────────
# Currently: section heading → all paragraphs → charts appended at end
# New:       section heading → paragraphs → then if 1 chart/map: text wraps
#            alongside; if 2 charts: text first then charts side by side
#
# For single chart: use a 2-col table (text col 60%, image col 40%)
# For two charts: text first, then side-by-side pair as before
# This ensures every page has substantial text alongside charts

OLD_SEC = """        story.append(Paragraph(h_clean.upper(), SS))
        for para in [p.strip() for p in b.split("\\n\\n") if p.strip()]:
            para = re.sub(r"\\*\\*(.*?)\\*\\*", r"<b>\\1</b>", para)
            para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
            para = para.replace("&", "&amp;")
            story.append(Paragraph(para, SB))

        charts_for_sec = processed_section_charts.get(h, [])
        if charts_for_sec:
            story.append(Spacer(1, 6))
            for i in range(0, len(charts_for_sec), 2):
                pair = charts_for_sec[i:i+2]"""

NEW_SEC = """        story.append(Paragraph(h_clean.upper(), SS))

        charts_for_sec = processed_section_charts.get(h, [])

        # Build text paragraphs
        text_paras = []
        for para in [p.strip() for p in b.split("\\n\\n") if p.strip()]:
            para = re.sub(r"\\*\\*(.*?)\\*\\*", r"<b>\\1</b>", para)
            para = re.sub(r"^[*-] ", "", para, flags=re.MULTILINE)
            para = para.replace("&", "&amp;")
            text_paras.append(Paragraph(para, SB))

        # Single chart/map: render text alongside image in a 2-col table
        if len(charts_for_sec) == 1:
            c = charts_for_sec[0]
            try:
                ow = c["width"] or 336; oh = c["height"] or 252
                # Image column = 45% of page width; text column = 55%
                img_col_w = pw * 0.44
                txt_col_w = pw * 0.52
                gap = pw * 0.04
                # Scale image to fit column, max height 8cm
                iw = img_col_w
                ih = iw * (oh / ow)
                if ih > 8 * cm:
                    ih = 8 * cm; iw = ih * (ow / oh)
                # For maps: don't upscale beyond natural size
                if c.get("is_map"):
                    nat_w = ow / 96 * 2.54 * cm
                    if nat_w < iw:
                        iw = nat_w; ih = iw * (oh / ow)

                img_elem = RLImage(io.BytesIO(c["image_data"]), width=iw, height=ih)
                cap_elem = Paragraph(f"Figure {c['fig_num']} — {c['fig_title']}", SFIG)
                # Build 2-column table: text left, image+caption right
                from reportlab.platypus import ListFlowable
                text_cell = text_paras  # list of paragraphs
                img_cell  = [cap_elem, img_elem]
                inline_t = Table([[text_cell, img_cell]],
                                  colWidths=[txt_col_w, img_col_w])
                inline_t.setStyle(TableStyle([
                    ("VALIGN",        (0,0), (-1,-1), "TOP"),
                    ("LEFTPADDING",   (0,0), (-1,-1), 0),
                    ("RIGHTPADDING",  (0,0), (0,-1), int(gap)),
                    ("RIGHTPADDING",  (1,0), (1,-1), 0),
                    ("TOPPADDING",    (0,0), (-1,-1), 0),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 0),
                ]))
                story.append(inline_t)
            except Exception as e:
                log.warning(f"Inline chart err: {e}")
                for tp in text_paras:
                    story.append(tp)
        else:
            # No charts or 2 charts: render text normally then charts below
            for tp in text_paras:
                story.append(tp)

        if len(charts_for_sec) == 2:
            story.append(Spacer(1, 6))
            for i in range(0, len(charts_for_sec), 2):
                pair = charts_for_sec[i:i+2]"""

assert OLD_SEC in src, "OLD_SEC not found"
src = src.replace(OLD_SEC, NEW_SEC, 1)
print("fix3 inline_text: OK")

# ── Fix 4: Close the for loop and section divider properly ────────────────────
# The original code had:
#   story.append(KeepTogether([t_cap, t_img]))
# story.append(HRFlowable(...))  <- after charts loop
#
# After our restructure the len==2 branch ends with KeepTogether then needs
# the section divider. The else branch (0 or 2 charts) already ends inside
# the for-i loop. We need to close it properly.
# The existing closing of the for loop is intact; we just need to ensure
# the section divider line is still there. Let's verify by checking it's in src.

if "story.append(HRFlowable(width=\"100%\", thickness=0.5, color=BORD, spaceAfter=4))" in src:
    print("fix4 divider: already present OK")
else:
    print("fix4 divider: NOT FOUND - needs manual check")

p.write_text(src)
print("Written OK")
