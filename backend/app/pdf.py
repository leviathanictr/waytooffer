from __future__ import annotations

import pathlib
import re


def _fix_typography(text: str) -> str:
    """Fix missing hyphens in compound words (Latin→Cyrillic and common Cyrillic prefixes)."""
    if not text:
        return text
    # NOTE: use actual Cyrillic chars in patterns — Python re does NOT support \uXXXX in raw strings
    # 1. Latin letter → Cyrillic: "SQLзапрос"→"SQL-запрос", "A/Bтест"→"A/B-тест"
    text = re.sub(r'([A-Za-z])([а-яёА-ЯЁ])', r'\1-\2', text)
    # Digit → 3+ Cyrillic chars (avoids "10пп", "1М+" false positives)
    text = re.sub(r'([0-9])([а-яёА-ЯЁ]{3,})', r'\1-\2', text)
    # 2. Always-compound Cyrillic prefixes
    text = re.sub(
        r'\b(веб|кейс|юнит|тайм|фитнес|питч|финтех|онлайн|реверс|логит)(?![-\s])([А-ЯЁа-яё])',
        r'\1-\2', text, flags=re.IGNORECASE,
    )
    # 3. Conditional prefixes — only before roots ≥4 Cyrillic chars
    #    NOTE: "продукт" removed — "продуктовый" is one word, not a compound
    text = re.sub(
        r'\b(бизнес|контент|медиа|нетворк)(?![-\s])([А-ЯЁа-яё]{4,})',
        r'\1-\2', text, flags=re.IGNORECASE,
    )
    # 4. Specific fixes
    text = re.sub(r'\b([Dd]ata)\s*[Dd]riven\b', 'Data-driven', text)
    text = re.sub(r'\b([Dd]ata)\s*[Ss]cience\b', 'Data Science', text)
    text = re.sub(r'\b([Dd]ata)\s*[Ss]cientist\b', 'Data Scientist', text)
    text = re.sub(r'\b([Dd]ata)\s*[Aa]nalyst\b', 'Data Analyst', text)
    text = re.sub(r'(?i)\bRESTful\s*API\b', 'REST API', text)
    text = re.sub(r'(?i)\bRESTful(?=[A-Z])', 'REST ', text)
    text = re.sub(r'(?i)\bпричинно\s*следственн', 'причинно-следственн', text)
    text = re.sub(r'(?i)\bscikitlearn\b', 'scikit-learn', text)
    text = re.sub(r'\bТ([Бб]анк)', r'Т-\1', text)
    return text

# ---------------------------------------------------------------------------
# Font discovery
# ---------------------------------------------------------------------------

_FONT_PAIRS = [
    ("C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/calibri.ttf",  "C:/Windows/Fonts/calibrib.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/freefont/FreeSans.ttf",
     "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
]

_FONT_REG: str | None = None
_FONT_BOLD: str | None = None
for _r, _b in _FONT_PAIRS:
    if pathlib.Path(_r).exists() and pathlib.Path(_b).exists():
        _FONT_REG, _FONT_BOLD = _r, _b
        break


# ---------------------------------------------------------------------------
# PDF builder (fpdf2 — works on Windows without GTK3)
# ---------------------------------------------------------------------------

def _build_fpdf(data: dict) -> bytes:
    from fpdf import FPDF

    RED   = (170, 25, 25)
    DARK  = (25, 25, 25)
    GREY  = (95, 95, 95)
    LGREY = (200, 200, 200)

    pdf = FPDF(format="A4")
    LM, TM, RM = 16, 16, 16
    pdf.set_margins(LM, TM, RM)
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()

    if _FONT_REG and _FONT_BOLD:
        pdf.add_font("F", "",  _FONT_REG)
        pdf.add_font("F", "B", _FONT_BOLD)
        FN = "F"
    else:
        FN = "Helvetica"

    W   = pdf.w - LM - RM          # ≈ 178 mm
    LW  = W * 0.615                 # left column  ≈ 109 mm
    GAP = 7.0                       # gap between columns
    RW  = W - LW - GAP             # right column ≈ 62 mm
    RX  = LM + LW + GAP            # right column X

    _DASH_VALUES = {"—", "–", "-", "−", "null", "None", "undefined", "н/д", "нет"}

    def safe(v, default="") -> str:
        if not v:
            return default
        raw = _fix_typography(str(v).strip())
        return default if raw in _DASH_VALUES else raw

    # ── DATA ─────────────────────────────────────────────────────────────────
    p        = data.get("personal") or {}
    education = data.get("education") or []
    experience = data.get("experience") or []
    skills   = data.get("skills") or {}
    languages = data.get("languages") or []
    extra    = data.get("extra") or {}

    name    = safe(p.get("name"), "Без имени")
    city    = safe(p.get("city"))
    phone   = safe(p.get("phone"))
    email   = safe(p.get("email"))
    links   = [safe(l) for l in (p.get("links") or []) if safe(l)]
    about   = safe(p.get("about"))
    hard    = [safe(s) for s in (skills.get("hard") or []) if safe(s)]
    soft    = [safe(s) for s in (skills.get("soft") or []) if safe(s)]

    # ── HEADER ───────────────────────────────────────────────────────────────
    # Name (left) + contact info (right) on same baseline
    contact = []
    if city:  contact.append(city)
    if phone: contact.append(phone)
    if email: contact.append(email)
    for lnk in links:
        contact.append(lnk)

    start_y = pdf.get_y()

    # Name
    pdf.set_font(FN, "B", 22)
    pdf.set_text_color(*DARK)
    pdf.set_xy(LM, start_y)
    pdf.multi_cell(LW, 9, name, align="L")
    name_end_y = pdf.get_y()

    # Contact (right, stacked)
    pdf.set_font(FN, "", 8.5)
    pdf.set_text_color(*GREY)
    cy = start_y
    for line in contact:
        pdf.set_xy(RX, cy)
        pdf.cell(RW, 5, line, align="R")
        cy += 5

    # About (under name, full left column width)
    if about:
        pdf.set_xy(LM, name_end_y + 1)
        pdf.set_font(FN, "", 9)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(LW, 4.5, about, align="L")

    header_end_y = max(pdf.get_y(), cy) + 3
    pdf.set_draw_color(*LGREY)
    pdf.set_line_width(0.4)
    pdf.line(LM, header_end_y, LM + W, header_end_y)

    content_y = header_end_y + 5  # both columns start here

    # ── LEFT COLUMN HELPERS ──────────────────────────────────────────────────
    def left_sec(title: str) -> None:
        pdf.set_font(FN, "B", 9.5)
        pdf.set_text_color(*RED)
        pdf.set_xy(LM, pdf.get_y())
        pdf.cell(LW, 5.5, title.upper(), ln=True)
        y = pdf.get_y()
        pdf.set_draw_color(*LGREY)
        pdf.line(LM, y, LM + LW - 2, y)
        pdf.ln(3)

    def left_text(txt: str, size=9, bold=False, color=DARK, after=1.0) -> None:
        if not txt:
            return
        pdf.set_font(FN, "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.set_x(LM)
        pdf.multi_cell(LW, 4.5, txt, align="L")
        if after:
            pdf.ln(after)

    # ── RIGHT COLUMN HELPERS ─────────────────────────────────────────────────
    # We track right-column Y separately
    r_y = content_y

    def right_sec(title: str) -> None:
        nonlocal r_y
        pdf.set_font(FN, "B", 9.5)
        pdf.set_text_color(*RED)
        pdf.set_xy(RX, r_y)
        pdf.cell(RW, 5.5, title.upper(), ln=False)
        r_y += 5.5
        pdf.set_draw_color(*LGREY)
        pdf.line(RX, r_y, RX + RW, r_y)
        r_y += 3

    def right_line(txt: str, size=9, bold=False, color=DARK, after=1.5) -> None:
        nonlocal r_y
        if not txt:
            return
        pdf.set_font(FN, "B" if bold else "", size)
        pdf.set_text_color(*color)
        # Use margin trick so multi_cell wraps at RX+RW
        old_lm = pdf.l_margin
        old_rm = pdf.r_margin
        pdf.set_left_margin(RX)
        pdf.set_right_margin(pdf.w - RX - RW)
        pdf.set_xy(RX, r_y)
        pdf.multi_cell(RW, 4.5, txt, align="L")
        pdf.set_left_margin(old_lm)
        pdf.set_right_margin(old_rm)
        r_y = pdf.get_y() + after

    # ── LEFT COLUMN ──────────────────────────────────────────────────────────
    pdf.set_y(content_y)

    if education:
        left_sec("Образование")
        for edu in education:
            uni = safe(edu.get("university"))
            if uni:
                left_text(uni, bold=True, size=10, after=0)
            parts = [p_ for p_ in [safe(edu.get("faculty")), safe(edu.get("speciality"))] if p_]
            yr = safe(edu.get("year"))
            if yr:
                parts.append(yr)
            if parts:
                left_text(" · ".join(parts), size=8.5, color=GREY, after=0)
            ach = safe(edu.get("achievements"))
            if ach:
                left_text(ach, size=8.5, after=0)
            pdf.ln(4)

    projects = []
    for proj in (extra.get("projects") or []):
        ps = safe(proj) if isinstance(proj, str) else safe(
            (proj or {}).get("name") or (proj or {}).get("url") or
            (proj or {}).get("title") or str(proj)
        )
        if ps:
            projects.append(ps)

    if projects:
        left_sec("Проекты")
        for ps in projects:
            left_text(ps, size=9, after=2)

    if experience:
        left_sec("Опыт и участие")
        for exp in experience:
            title_ = safe(exp.get("title"))
            if title_:
                left_text(title_, bold=True, size=10, color=DARK, after=0)
            role = safe(exp.get("role"))
            if role:
                left_text(role, size=8.5, color=GREY, after=0)
            desc = safe(exp.get("description"))
            if desc:
                left_text(desc, size=9, after=0)
            result = safe(exp.get("result"))
            if result:
                left_text(f"Результат: {result}", size=9, bold=True, color=DARK, after=0)
            pdf.ln(4)

    hobbies = safe(extra.get("hobbies"))
    if hobbies:
        left_sec("Дополнительная информация")
        left_text(hobbies, size=9, after=0)

    left_end_page = pdf.page
    left_end_y = pdf.get_y()

    # ── RIGHT COLUMN ─────────────────────────────────────────────────────────
    # Switch back to page 1 so the right column starts alongside the left column
    # even when the left column has flowed onto subsequent pages.
    pdf.page = 1

    if hard or soft:
        right_sec("Навыки")
        if hard:
            right_line(" · ".join(hard), size=8.5, after=2)
        if soft:
            right_line(" · ".join(soft), size=8.5, color=GREY, after=2)
        r_y += 3

    if languages:
        right_sec("Языки")
        for lang in languages:
            lng = safe(lang.get("language"))
            lvl = safe(lang.get("level"))
            if lng:
                right_line(f"{lng}{f' ({lvl})' if lvl else ''}", size=9)

    # Restore cursor to the end of the left column
    pdf.page = left_end_page
    pdf.set_y(max(left_end_y, r_y if left_end_page == 1 else left_end_y))
    return bytes(pdf.output())


# ---------------------------------------------------------------------------
# WeasyPrint path (Linux/Mac prod) — kept for HTML rendering
# ---------------------------------------------------------------------------

def _render_weasyprint(html: str) -> bytes:
    from weasyprint import HTML as _W
    return _W(string=html).write_pdf()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf(resume_data: dict) -> bytes:
    try:
        return _render_weasyprint(_build_html(resume_data))
    except Exception:
        return _build_fpdf(resume_data)


# ---------------------------------------------------------------------------
# HTML template (WeasyPrint, Linux prod)
# ---------------------------------------------------------------------------

def _build_html(resume_data: dict) -> str:
    p        = resume_data.get("personal") or {}
    education = resume_data.get("education") or []
    experience = resume_data.get("experience") or []
    skills   = resume_data.get("skills") or {}
    languages = resume_data.get("languages") or []
    extra    = resume_data.get("extra") or {}

    _DASH_HTML = {"—", "–", "-", "−", "null", "None", "undefined", "н/д", "нет"}

    def s(v, d=""):
        if not v:
            return d
        raw = _fix_typography(str(v).strip())
        return d if raw in _DASH_HTML else raw
    def e(t): return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

    name = e(s(p.get("name"), "Без имени"))
    contact = []
    if s(p.get("city")): contact.append(e(s(p["city"])))
    if s(p.get("phone")): contact.append(e(s(p["phone"])))
    if s(p.get("email")): contact.append(f'<a href="mailto:{e(s(p["email"]))}">{e(s(p["email"]))}</a>')
    for lnk in (p.get("links") or []):
        ls = s(lnk)
        if ls: contact.append(f'<a href="{e(ls)}">{e(ls)}</a>')
    contact_html = "<br>".join(contact)
    about_html = f'<p class="about">{e(s(p.get("about")))}</p>' if s(p.get("about")) else ""

    def edu_html():
        if not education: return ""
        items = ""
        for edu in education:
            uni = e(s(edu.get("university")))
            dets = " · ".join(filter(None,[e(s(edu.get("faculty"))),e(s(edu.get("speciality"))),s(edu.get("year"))]))
            ach = e(s(edu.get("achievements")))
            items += f'<div class="item"><b>{uni}</b>{f"<br><span class=d>{dets}</span>" if dets else ""}{f"<br><span class=d>✦ {ach}</span>" if ach else ""}</div>'
        return f'<div class="sec"><div class="sec-t">Образование</div>{items}</div>'

    def exp_html():
        if not experience: return ""
        items = ""
        for exp in experience:
            t_=e(s(exp.get("title"))); r_=e(s(exp.get("role"))); d_=e(s(exp.get("description"))); rs=e(s(exp.get("result")))
            items += f'<div class="item"><b style="color:#1E3A5F">{t_}</b>{f"<br><span class=d>{r_}</span>" if r_ else ""}{f"<br>{d_}" if d_ else ""}{f"<br><b>Результат: {rs}</b>" if rs else ""}</div>'
        return f'<div class="sec"><div class="sec-t">Опыт и участие</div>{items}</div>'

    def proj_html():
        ps = []
        for proj in (extra.get("projects") or []):
            pst = s(proj) if isinstance(proj,str) else s((proj or {}).get("name") or (proj or {}).get("url") or str(proj))
            if pst: ps.append(pst)
        if not ps: return ""
        items = "".join(f'<div class="item">{e(p_)}</div>' for p_ in ps)
        return f'<div class="sec"><div class="sec-t">Проекты</div>{items}</div>'

    def hob_html():
        hob = s(extra.get("hobbies"))
        if not hob: return ""
        return f'<div class="sec"><div class="sec-t">Дополнительно</div><div class="item">{e(hob)}</div></div>'

    def skills_html():
        hard=[s(x) for x in (skills.get("hard") or []) if s(x)]
        soft=[s(x) for x in (skills.get("soft") or []) if s(x)]
        if not hard and not soft: return ""
        out = ""
        if hard:
            out += f'<div style="font-size:8.5pt;line-height:1.7;margin-bottom:4px">{e(" · ".join(hard))}</div>'
        if soft:
            out += f'<div style="font-size:8pt;color:#666;line-height:1.7">{e(" · ".join(soft))}</div>'
        return f'<div class="sec"><div class="sec-t">Навыки</div>{out}</div>'

    def lang_html():
        if not languages: return ""
        rows = ""
        for lang in languages:
            lg=e(s(lang.get("language"))); lv=e(s(lang.get("level")))
            if lg: rows += f"<div>{lg}{f' ({lv})' if lv else ''}</div>"
        return f'<div class="sec"><div class="sec-t">Языки</div>{rows}</div>' if rows else ""

    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"/>
<style>
@page{{size:A4;margin:16mm}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;font-size:9.5pt;line-height:1.45;color:#191919}}
.header{{overflow:hidden;border-bottom:2px solid #ccc;padding-bottom:10px;margin-bottom:14px}}
.h-name{{font-size:21pt;font-weight:700;color:#111;line-height:1.1}}
.about{{font-size:9pt;color:#333;margin-top:6px}}
.h-contact{{float:right;width:36%;text-align:right;font-size:8.5pt;color:#555;line-height:1.7}}
.h-contact a{{color:#555;text-decoration:none}}
.h-main{{overflow:hidden}}
.layout{{overflow:hidden}}
.right-col{{float:right;width:36%;padding-left:7mm}}
.left-col{{overflow:hidden}}
.sec{{margin-bottom:14px;page-break-inside:avoid}}
.sec-t{{font-size:9.5pt;font-weight:700;color:#aa1919;text-transform:uppercase;border-bottom:1px solid #ddd;padding-bottom:2px;margin-bottom:6px}}
.item{{margin-bottom:7px;font-size:9pt}}.d{{color:#666;font-size:8.5pt}}
a{{color:#1E3A5F;text-decoration:none}}
</style></head><body>
<div class="header">
  <div class="h-contact">{contact_html}</div>
  <div class="h-main"><div class="h-name">{name}</div>{about_html}</div>
</div>
<div class="layout">
  <div class="right-col">{skills_html()}{lang_html()}</div>
  <div class="left-col">{edu_html()}{proj_html()}{exp_html()}{hob_html()}</div>
</div>
</body></html>"""
