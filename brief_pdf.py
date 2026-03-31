"""
brief_pdf.py - Intelligence Brief PDF generation for Meridian.
"""
import io, re, sqlite3, logging, threading, datetime, urllib.request, json
from pathlib import Path

log = logging.getLogger("meridian")

def _tok(text):
    return set(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())

def score_charts_for_section(section_text, charts, max_charts=4):
    section_tokens = _tok(section_text)
    if not section_tokens:
        return []
    scored = []
    for c in charts:
        score = len(_tok(c.get("insight","")) & section_tokens)*2 + len(_tok(c.get("description","")) & section_tokens)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    result, seen = [], set()
    for _, c in scored:
        aid = c.get("article_id")
        if aid not in seen:
            seen.add(aid)
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
    AMBER=HexColor("#c4783a"); MID=HexColor("#555555"); LIGHT=HexColor("#888888")
    DARK=HexColor("#1a1a1a"); BORD=HexColor("#ddd8cc")
    def S(name, **kw):
        d=dict(fontName="Helvetica",fontSize=10,leading=14,textColor=DARK,spaceAfter=0,spaceBefore=0)
        d.update(kw); return ParagraphStyle(name, **d)
    SE=S("e",fontSize=7,textColor=AMBER,fontName="Helvetica-Bold",letterSpacing=1.5,spaceAfter=4)
    ST=S("t",fontSize=22,fontName="Helvetica-Bold",leading=26,spaceAfter=6)
    SM=S("m",fontSize=8,textColor=LIGHT,spaceAfter=16)
    SS=S("s",fontSize=8,textColor=AMBER,fontName="Helvetica-Bold",letterSpacing=1.2,spaceAfter=8,spaceBefore=20)
    SB=S("b",fontSize=10,leading=16,textColor=MID,spaceAfter=10)
    SF=S("f",fontSize=7,textColor=LIGHT,letterSpacing=0.8)
    article_ids=[a.get("id") for a in articles if a.get("id")]
    all_charts=[]
    if article_ids and db_path:
        ph=",".join("?"*len(article_ids))
        with sqlite3.connect(db_path) as cx:
            rows=cx.execute(
                f"SELECT id,article_id,caption,description,insight,image_data,width,height "
                f"FROM article_images WHERE article_id IN ({ph}) "
                "AND insight!= AND insight IS NOT NULL AND image_data IS NOT NULL",
                article_ids).fetchall()
        for r in rows:
            all_charts.append({"id":r[0],"article_id":r[1],"caption":r[2],
                "description":r[3],"insight":r[4],"image_data":r[5],"width":r[6],"height":r[7]})
    log.info(f"Brief PDF: {len(all_charts)} charts for {len(article_ids)} articles")
    def parse_sections(text):
        parts=re.split(r"
(?=## )",text.strip()); secs=[]
        for part in parts:
            part=part.strip()
            if not part: continue
            if part.startswith("## "):
                lines2=part[3:].split("
",1)
                h=lines2[0].strip(); b=lines2[1].strip() if len(lines2)>1 else ""
            else:
                h="Overview"; b=part
            if b: secs.append({"heading":h,"body":b})
        return secs
    sections=parse_sections(brief_text)
    sources=sorted(set(a.get("source","") for a in articles if a.get("source","")))
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=2.2*cm,rightMargin=2.2*cm,
        topMargin=2*cm,bottomMargin=2*cm,title=theme.get("name","Brief")+" - Intelligence Brief")
    pw=A4[0]-4.4*cm; story=[]
    emoji=theme.get("emoji",""); name=theme.get("name","Intelligence Brief")
    today=datetime.date.today().strftime("%d %B %Y")
    story.append(Paragraph(f"{emoji}  {name.upper()} - INTELLIGENCE BRIEF", SE))
    story.append(Paragraph(name, ST))
    story.append(Paragraph(f"Meridian Intelligence  .  {today}  .  {len(articles)} articles  .  {len(sources)} sources", SM))
    story.append(HRFlowable(width="100%",thickness=2,color=AMBER,spaceAfter=20))
    used,total_used,MAX=set(),0,8
    for sec in sections:
        h,b=sec["heading"],sec["body"]
        story.append(Paragraph(h.upper(), SS))
        for para in [p.strip() for p in b.split("

") if p.strip()]:
            para=re.sub(r"\*\*(.*?)\*\*",r"<b></b>",para)
            para=re.sub(r"^[*-] ","",para,flags=re.MULTILINE)
            para=para.replace("&","&amp;")
            story.append(Paragraph(para, SB))
        if brief_type=="full" and all_charts and total_used<MAX:
            candidates=[c for c in all_charts if c["id"] not in used]
            selected=score_charts_for_section(h+" "+b,candidates,max_charts=min(4,MAX-total_used))
            if selected:
                story.append(Spacer(1,8)); cw=(pw-0.5*cm)/2
                for i in range(0,len(selected),2):
                    pair=selected[i:i+2]; cells=[]
                    for c in pair:
                        try:
                            ow=c["width"] or 336; oh=c["height"] or 379
                            asp=oh/ow; iw=cw; ih=iw*asp
                            if ih>7*cm: ih=7*cm; iw=ih/asp
                            cells.append(RLImage(io.BytesIO(c["image_data"]),width=iw,height=ih))
                            used.add(c["id"]); total_used+=1
                        except Exception as e:
                            log.warning(f"Chart err: {e}"); cells.append(Paragraph("",SB))
                    while len(cells)<2: cells.append("")
                    t=Table([cells],colWidths=[cw,cw])
                    t.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),
                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),0),
                        ("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),4),
                        ("BOTTOMPADDING",(0,0),(-1,-1),4)]))
                    story.append(KeepTogether(t))
                story.append(Spacer(1,8))
        story.append(HRFlowable(width="100%",thickness=0.5,color=BORD,spaceAfter=4))
    if sources:
        story.append(Spacer(1,12))
        story.append(Paragraph("Sources: "+"  .  ".join(sources), SF))
    doc.build(story)
    return buf.getvalue()

_pdf_jobs={}

def get_job(job_id):
    return _pdf_jobs.get(job_id)

def start_pdf_job(job_id, theme, articles, brief_type, db_path, base_dir):
    _pdf_jobs[job_id]={"status":"running","error":None,"ready":False}
    def _run():
        try:
            cp=Path(base_dir)/"credentials.json"
            api_key=json.loads(cp.read_text()).get("anthropic_api_key","") if cp.exists() else ""
            ctx="

---

".join(
                "SOURCE: "+a.get("source","")+"
TITLE: "+a.get("title","")+"
SUMMARY: "+a.get("summary","")
                for a in articles if a.get("summary"))
            name=theme.get("name",""); em=theme.get("emoji",""); subs=theme.get("subtopics",[])
            if brief_type=="short":
                prompt=(f"You are a senior intelligence analyst. Write a concise intelligence brief on "{name}"."
                    "

Structure:
## Executive Summary
[2-3 sentences]

"
                    "## Key Developments
[5-7 bullets]

"
                    f"## Strategic Implications
[2-3 paragraphs]

## Watch List
[3-5 items]

ARTICLES:
{ctx}")
                mt=1500
            else:
                ss="

".join(f"## {s}
[2-3 paragraphs of analytical prose]" for s in subs)
                prompt=(f"You are a senior intelligence analyst. Write a comprehensive intelligence brief on "{name}"."
                    f"

Structure:
## {em} {name} - Intelligence Brief

## Executive Summary
[3-4 sentences]

"
                    +ss+"

## Cross-cutting Themes
[overarching patterns]

"
                    f"## Strategic Implications
[forward-looking analysis]

ARTICLES:
{ctx}")
                mt=4000
            data=json.dumps({"model":"claude-sonnet-4-20250514","max_tokens":mt,
                "messages":[{"role":"user","content":prompt}]}).encode()
            req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=data,
                headers={"Content-Type":"application/json","x-api-key":api_key,"anthropic-version":"2023-06-01"},
                method="POST")
            with urllib.request.urlopen(req,timeout=180) as r:
                brief_text=json.loads(r.read())["content"][0]["text"]
            pdf=build_brief_pdf(theme,articles,brief_text,brief_type,db_path)
            out=Path(base_dir)/f"tmp_brief_{job_id}.pdf"
            out.write_bytes(pdf)
            _pdf_jobs[job_id]={"status":"done","error":None,"ready":True,"path":str(out),"size":len(pdf)}
            log.info(f"Brief PDF {job_id}: done ({len(pdf)//1024}KB)")
        except Exception as e:
            log.error(f"Brief PDF {job_id}: {e}",exc_info=True)
            _pdf_jobs[job_id]={"status":"error","error":str(e),"ready":False}
    import threading
    threading.Thread(target=_run,daemon=True).start()