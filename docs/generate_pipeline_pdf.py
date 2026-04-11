"""
Meridian — Pipeline PDF generator
Produces docs/meridian_pipeline.pdf using reportlab only (no cairo/cairosvg needed).

Requirements: pip3 install reportlab
Usage:        python3 docs/generate_pipeline_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import (Drawing, Rect, Line, String, Path,
                                        Group, PolyLine)
from reportlab.graphics import renderPDF
from reportlab.platypus import Flowable
from pathlib import Path

OUT = Path(__file__).parent / "meridian_pipeline.pdf"

# ── Colours ───────────────────────────────────────────────────────────────────
TEAL_FILL   = colors.HexColor("#9FE1CB")
TEAL_STROKE = colors.HexColor("#0F6E56")
TEAL_TEXT   = colors.HexColor("#085041")
PUR_FILL    = colors.HexColor("#CECBF6")
PUR_STROKE  = colors.HexColor("#534AB7")
PUR_TEXT    = colors.HexColor("#3C3489")
AMB_FILL    = colors.HexColor("#FAC775")
AMB_STROKE  = colors.HexColor("#854F0B")
AMB_TEXT    = colors.HexColor("#633806")
GRY_FILL    = colors.HexColor("#D3D1C7")
GRY_STROKE  = colors.HexColor("#5F5E5A")
GRY_TEXT    = colors.HexColor("#2C2C2A")
MUT_TEXT    = colors.HexColor("#5F5E5A")
TEAL_HDR    = colors.HexColor("#085041")
RULE        = colors.HexColor("#e4dfd4")
STRIPE      = colors.HexColor("#f0ece3")
WHITE       = colors.white

def box(d, x, y, w, h, fill, stroke, label, sublabel=None, cost=None,
        label_color=GRY_TEXT, muted=MUT_TEXT, r=6):
    d.add(Rect(x, y, w, h, rx=r, ry=r,
               fillColor=fill, strokeColor=stroke, strokeWidth=0.5))
    if sublabel:
        d.add(String(x+w/2, y+h-14, label,
                     fontSize=10, fontName="Helvetica-Bold",
                     fillColor=label_color, textAnchor="middle"))
        d.add(String(x+w/2, y+h-26, sublabel,
                     fontSize=9, fontName="Helvetica",
                     fillColor=label_color, textAnchor="middle"))
    else:
        d.add(String(x+w/2, y+h/2+4, label,
                     fontSize=10, fontName="Helvetica-Bold",
                     fillColor=label_color, textAnchor="middle"))
    if cost:
        d.add(String(x+w/2, y-10, cost,
                     fontSize=8, fontName="Helvetica",
                     fillColor=muted, textAnchor="middle"))

def arrow(d, x1, y1, x2, y2, dashed=False):
    dash = [4, 3] if dashed else None
    d.add(Line(x1, y1, x2, y2,
               strokeColor=GRY_STROKE, strokeWidth=0.8,
               strokeDashArray=dash))
    # Arrowhead pointing down (y decreases in reportlab coords)
    dy = y2 - y1
    dx = x2 - x1
    import math
    angle = math.atan2(dy, dx)
    size = 5
    ax1 = x2 - size * math.cos(angle - 0.4)
    ay1 = y2 - size * math.sin(angle - 0.4)
    ax2 = x2 - size * math.cos(angle + 0.4)
    ay2 = y2 - size * math.sin(angle + 0.4)
    d.add(Line(x2, y2, ax1, ay1, strokeColor=GRY_STROKE, strokeWidth=0.8))
    d.add(Line(x2, y2, ax2, ay2, strokeColor=GRY_STROKE, strokeWidth=0.8))

class DiagramFlowable(Flowable):
    """Renders the pipeline diagram as a reportlab Drawing."""
    def __init__(self, width, height):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        d = Drawing(self.width, self.height)
        W, H = self.width, self.height
        # Scale factor: original SVG is 680 wide, 740 tall
        sx = W / 680
        sy = H / 740

        def tx(x): return x * sx
        def ty(y): return H - y * sy  # flip Y for reportlab

        BW, BH = tx(180), ty(0) - ty(56)  # box width/height

        def rbox(x, y, fill, stroke, label, sub=None, cost=None, tc=GRY_TEXT):
            rx, ry = tx(x), ty(y+56)
            d.add(Rect(rx, ry, BW, BH, rx=4, ry=4,
                       fillColor=fill, strokeColor=stroke, strokeWidth=0.5))
            if sub:
                d.add(String(rx+BW/2, ry+BH-13, label,
                             fontSize=9, fontName="Helvetica-Bold",
                             fillColor=tc, textAnchor="middle"))
                d.add(String(rx+BW/2, ry+BH-25, sub,
                             fontSize=8, fontName="Helvetica",
                             fillColor=tc, textAnchor="middle"))
            else:
                d.add(String(rx+BW/2, ry+BH/2+4, label,
                             fontSize=9, fontName="Helvetica-Bold",
                             fillColor=tc, textAnchor="middle"))
            if cost:
                d.add(String(rx+BW/2, ry-12, cost,
                             fontSize=7.5, fontName="Helvetica",
                             fillColor=MUT_TEXT, textAnchor="middle"))

        def ln(x1, y1, x2, y2, dashed=False):
            dash = [3, 2] if dashed else None
            d.add(Line(tx(x1), ty(y1), tx(x2), ty(y2),
                       strokeColor=GRY_STROKE, strokeWidth=0.7,
                       strokeDashArray=dash))
            # Tiny arrowhead
            import math
            dx, dy2 = tx(x2)-tx(x1), ty(y2)-ty(y1)
            ang = math.atan2(dy2, dx)
            sz = 4
            for sign in (-0.4, 0.4):
                d.add(Line(tx(x2), ty(y2),
                           tx(x2) - sz*math.cos(ang-sign),
                           ty(y2) - sz*math.sin(ang-sign),
                           strokeColor=GRY_STROKE, strokeWidth=0.7))

        # ── Headers ──
        for x, fill, stroke, label, tc in [
            (30,  TEAL_FILL, TEAL_STROKE, "Saved articles", TEAL_TEXT),
            (250, PUR_FILL,  PUR_STROKE,  "AI picks",        PUR_TEXT),
            (470, AMB_FILL,  AMB_STROKE,  "Key Themes & briefs", AMB_TEXT),
        ]:
            rx, ry = tx(x), ty(56)
            d.add(Rect(rx, ry, BW, ty(20)-ty(56), rx=4, ry=4,
                       fillColor=fill, strokeColor=stroke, strokeWidth=0.5))
            d.add(String(rx+BW/2, ry+(ty(20)-ty(56))/2+3, label,
                         fontSize=10, fontName="Helvetica-Bold",
                         fillColor=tc, textAnchor="middle"))

        # ── Step 1 ──
        rbox(30,  90, TEAL_FILL, TEAL_STROKE, "Playwright scraper", "FT · Economist · FA", "2x/day · $0", TEAL_TEXT)
        rbox(250, 90, PUR_FILL,  PUR_STROKE,  "AI pick web search", "Haiku + web_search", "1x/day · ~$0.08", PUR_TEXT)
        rbox(470, 90, AMB_FILL,  AMB_STROKE,  "KT seed", "Sonnet + Haiku", "Manual · ~$0.33/run", AMB_TEXT)

        ln(120, 146, 120, 196); ln(340, 146, 340, 196); ln(560, 146, 560, 196)

        # ── Step 2 ──
        rbox(30,  196, TEAL_FILL, TEAL_STROKE, "Article enrichment", "Haiku summary + tags", "2x/day · ~$0.03", TEAL_TEXT)
        rbox(250, 196, PUR_FILL,  PUR_STROKE,  "Score articles", ">=8 Feed · 6-7 Suggested", "included above", PUR_TEXT)
        rbox(470, 196, AMB_FILL,  AMB_STROKE,  "kt/tag-new", "Assign to themes", "1x/day · ~$0.01", AMB_TEXT)

        ln(120, 252, 120, 302); ln(340, 252, 340, 302); ln(560, 252, 560, 302)

        # ── Step 3 ──
        rbox(30,  302, TEAL_FILL, TEAL_STROKE, "Push to VPS", "Articles, images, newsletters", "2x/day · $0", TEAL_TEXT)
        rbox(30,  408, GRY_FILL,  GRY_STROKE,  "Newsletter sync", "iCloud IMAP pull", "2x/day · $0", GRY_TEXT)
        rbox(250, 302, PUR_FILL,  PUR_STROKE,  "Suggested inbox", "Score 6-7 for review", "passive · $0", PUR_TEXT)
        rbox(470, 302, AMB_FILL,  AMB_STROKE,  "Key Themes panel", "8 themes, key facts", "passive · $0", AMB_TEXT)

        ln(120, 358, 120, 408); ln(340, 358, 340, 440); ln(560, 358, 560, 440)

        # ── Step 4 ──
        rbox(250, 440, PUR_FILL, PUR_STROKE, "Dismiss feedback", "Negative signal loop", "passive · $0", PUR_TEXT)
        rbox(470, 440, AMB_FILL, AMB_STROKE, "Briefing generator", "Sonnet, on demand", "Manual · ~$0.25/run", AMB_TEXT)

        # Feedback dashed loop
        d.add(Line(tx(252), ty(462), tx(210), ty(462), strokeColor=GRY_STROKE, strokeWidth=0.5, strokeDashArray=[3,2]))
        d.add(Line(tx(210), ty(462), tx(210), ty(196), strokeColor=GRY_STROKE, strokeWidth=0.5, strokeDashArray=[3,2]))
        d.add(Line(tx(210), ty(196), tx(250), ty(196), strokeColor=GRY_STROKE, strokeWidth=0.5, strokeDashArray=[3,2]))

        # Cross-feed dashed
        d.add(Line(tx(210), ty(340), tx(250), ty(302), strokeColor=GRY_STROKE, strokeWidth=0.5, strokeDashArray=[2,2]))

        # ── Divider ──
        d.add(Line(tx(30), ty(540), tx(650), ty(540),
                   strokeColor=colors.HexColor("#B4B2A9"), strokeWidth=0.5,
                   strokeDashArray=[4,3]))
        d.add(String(tx(340), ty(558)+4, "shared output",
                     fontSize=8, fontName="Helvetica",
                     fillColor=MUT_TEXT, textAnchor="middle"))

        # ── Output boxes ──
        out_h = ty(570) - ty(614)
        for x, label in [(30, "News Feed"), (255, "Key Themes"), (480, "Intelligence Brief")]:
            w = tx(170)
            d.add(Rect(tx(x), ty(614), w, out_h, rx=4, ry=4,
                       fillColor=GRY_FILL, strokeColor=GRY_STROKE, strokeWidth=0.5))
            d.add(String(tx(x)+w/2, ty(614)+out_h/2+3, label,
                         fontSize=9, fontName="Helvetica-Bold",
                         fillColor=GRY_TEXT, textAnchor="middle"))

        ln(115, 496, 115, 570); ln(340, 496, 340, 570); ln(560, 496, 565, 570)

        # ── Health check ──
        hx, hy = tx(470), ty(674)
        hh = ty(630) - ty(674)
        d.add(Rect(hx, hy, BW, hh, rx=4, ry=4,
                   fillColor=GRY_FILL, strokeColor=GRY_STROKE, strokeWidth=0.5))
        d.add(String(hx+BW/2, hy+hh-13, "Health check panel",
                     fontSize=8, fontName="Helvetica-Bold",
                     fillColor=GRY_TEXT, textAnchor="middle"))
        d.add(String(hx+BW/2, hy+hh-25, "On demand · ~$0.01/click",
                     fontSize=7.5, fontName="Helvetica",
                     fillColor=MUT_TEXT, textAnchor="middle"))

        # ── Total ──
        d.add(String(tx(120), ty(650)+4, "Total est.",
                     fontSize=8, fontName="Helvetica", fillColor=MUT_TEXT, textAnchor="middle"))
        d.add(String(tx(120), ty(668)+4, "~$0.18-0.25/day",
                     fontSize=10, fontName="Helvetica-Bold", fillColor=GRY_TEXT, textAnchor="middle"))

        renderPDF.draw(d, self.canv, 0, 0)

    def wrap(self, aW, aH):
        return self.width, self.height

# ── Build PDF ─────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(str(OUT), pagesize=A4,
    leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)

title_s   = ParagraphStyle("t",  fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#1a1a1a"), spaceAfter=4)
sub_s     = ParagraphStyle("s",  fontName="Helvetica",      fontSize=10, textColor=colors.HexColor("#888780"), spaceAfter=16)
section_s = ParagraphStyle("h",  fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#1a1a1a"), spaceBefore=20, spaceAfter=10)
note_s    = ParagraphStyle("n",  fontName="Helvetica",      fontSize=9,  textColor=colors.HexColor("#888780"), spaceAfter=4)
cell_s    = ParagraphStyle("c",  fontName="Helvetica",      fontSize=9,  textColor=colors.HexColor("#1a1a1a"), leading=13)
bold_s    = ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=9,  textColor=colors.HexColor("#1a1a1a"), leading=13)
hdr_s     = ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=9,  textColor=WHITE, leading=13)
ctr_s     = ParagraphStyle("cc", fontName="Helvetica",      fontSize=9,  textColor=colors.HexColor("#444441"), leading=13, alignment=TA_CENTER)
tot_s     = ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=9,  textColor=TEAL_HDR, leading=13, alignment=TA_CENTER)

def p(text, style=cell_s):
    return Paragraph(text.replace("\n", "<br/>"), style)

col_w = [doc.width * x for x in [0.30, 0.37, 0.16, 0.17]]
rows = [
    ["Playwright scraper\n(FT / Eco / FA)", "Opens a logged-in browser on your Mac, loads saved/bookmarked articles pages, extracts new titles and URLs since last run.", "2x", "$0"],
    ["Article enrichment\n(Haiku)", "Sends each new article to Haiku for a summary, tags, topic and pub date — populates the article card in your feed.", "2x", "~$0.03"],
    ["AI pick web search\n(Haiku + web_search)", "Searches the web for recent articles from FT, Economist, FA and Bloomberg matching your interest profile. Scores 0-10; >=8 goes straight to feed.", "1x (gated)", "~$0.08"],
    ["kt/tag-new\n(Haiku)", "Assigns any newly added articles to 1-2 of your 8 Key Themes, keeping the Key Themes panel current.", "1x (gated)", "~$0.01"],
    ["Newsletter sync", "Connects to iCloud IMAP and pulls new newsletter emails into the Newsletters tab.", "2x", "$0"],
    ["Push to VPS", "One-way sync of all articles, images, newsletters and interviews from local Mac DB to meridianreader.com.", "2x", "$0"],
    ["KT seed\n(Sonnet + Haiku)", "Full rebuild of Key Themes. Sonnet identifies 8 themes, Haiku assigns all articles, Haiku generates key facts and subtopics per theme.", "Manual\n(~1x/week)", "~$0.05\n(amortised)"],
    ["Briefing generator\n(Sonnet)", "Generates an intelligence brief from selected articles and themes. On-demand only.", "Manual", "~$0.25/run"],
    ["Health check panel\n(Haiku)", "Sends DB stats to Haiku which writes a 1-10 scored diagnosis shown at the top of the Stats section.", "On demand", "~$0.01\n/click"],
]

tbl_data = [[p(h, hdr_s) for h in ["Pipeline", "What it does", "Runs/day", "Cost/day"]]]
for row in rows:
    tbl_data.append([p(row[0], bold_s), p(row[1]), p(row[2], ctr_s), p(row[3], ctr_s)])

tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)
tbl.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0),  TEAL_HDR),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, STRIPE]),
    ("GRID",          (0,0), (-1,-1), 0.3, RULE),
    ("LINEBELOW",     (0,0), (-1,0),  0.8, TEAL_HDR),
    ("TOPPADDING",    (0,0), (-1,-1), 6),
    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ("LEFTPADDING",   (0,0), (-1,-1), 7),
    ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
]))

total_tbl = Table([[p(""), p(""), p("Total", ctr_s), p("~$0.18-0.25/day", tot_s)]], colWidths=col_w)
total_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#E1F5EE")),
    ("LINEABOVE",  (0,0), (-1,0),  0.8, TEAL_HDR),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 7),
    ("RIGHTPADDING",  (0,0), (-1,-1), 7),
    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
]))

avail_w = doc.width
diagram = DiagramFlowable(avail_w, avail_w * (740/680))

story = [
    Paragraph("Meridian — Pipeline Overview", title_s),
    Paragraph("API cost analysis · April 2026", sub_s),
    HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=16),
    Paragraph("Pipeline actions &amp; costs", section_s),
    tbl, total_tbl,
    Spacer(1, 24),
    Paragraph("Pipeline diagram", section_s),
    Paragraph("Three independent pipelines — saved articles (green), AI picks (purple), Key Themes &amp; briefs (amber) — converging on shared outputs. Dashed lines show cross-feed relationships.", note_s),
    Spacer(1, 8),
    diagram,
]

doc.build(story)
print(f"Written: {OUT}")
