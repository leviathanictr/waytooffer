from __future__ import annotations

import json

try:
    from weasyprint import HTML as _WeasyHTML  # noqa: F401
    def _render_pdf(html: str) -> bytes:
        return _WeasyHTML(string=html).write_pdf()  # type: ignore[return-value]
except Exception:
    def _render_pdf(_html: str) -> bytes:  # type: ignore[misc]
        raise RuntimeError(
            "WeasyPrint не установлен. На Windows установите GTK3 runtime: "
            "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer"
        )

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Резюме</title>
  <style>
    /* ------------------------------------------------------------------ */
    /* Reset & page setup                                                   */
    /* ------------------------------------------------------------------ */
    @page {{
      size: A4;
      margin: 18mm 18mm 18mm 18mm;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: Arial, Helvetica, sans-serif;
      font-size: 10pt;
      line-height: 1.45;
      color: #1a1a2e;
      background: #ffffff;
      max-width: 210mm;
    }}

    /* ------------------------------------------------------------------ */
    /* Header — personal block                                              */
    /* ------------------------------------------------------------------ */
    .header {{
      border-bottom: 3px solid #1E3A5F;
      padding-bottom: 12px;
      margin-bottom: 18px;
    }}

    .header h1 {{
      font-size: 22pt;
      font-weight: 700;
      color: #1E3A5F;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }}

    .header .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px 20px;
      font-size: 9pt;
      color: #444;
    }}

    .header .meta span::before {{
      content: "• ";
      color: #1E3A5F;
    }}

    .header .about {{
      margin-top: 8px;
      font-size: 9.5pt;
      color: #333;
      font-style: italic;
    }}

    /* ------------------------------------------------------------------ */
    /* Section headings                                                      */
    /* ------------------------------------------------------------------ */
    .section {{
      margin-bottom: 16px;
      page-break-inside: avoid;
    }}

    .section-title {{
      font-size: 11pt;
      font-weight: 700;
      color: #1E3A5F;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      border-bottom: 1.5px solid #c8d8f0;
      padding-bottom: 3px;
      margin-bottom: 8px;
    }}

    /* ------------------------------------------------------------------ */
    /* Education                                                             */
    /* ------------------------------------------------------------------ */
    .edu-item {{
      margin-bottom: 8px;
    }}

    .edu-item .edu-name {{
      font-weight: 700;
      font-size: 10pt;
    }}

    .edu-item .edu-detail {{
      font-size: 9pt;
      color: #555;
    }}

    .edu-item .edu-achievements {{
      font-size: 9pt;
      color: #333;
      margin-top: 2px;
    }}

    /* ------------------------------------------------------------------ */
    /* Experience                                                            */
    /* ------------------------------------------------------------------ */
    .exp-item {{
      margin-bottom: 10px;
    }}

    .exp-item .exp-title {{
      font-weight: 700;
      font-size: 10pt;
      color: #1E3A5F;
    }}

    .exp-item .exp-role {{
      font-size: 9.5pt;
      color: #555;
      margin-bottom: 2px;
    }}

    .exp-item .exp-desc {{
      font-size: 9.5pt;
      color: #333;
    }}

    .exp-item .exp-result {{
      font-size: 9pt;
      color: #1E3A5F;
      font-weight: 600;
      margin-top: 2px;
    }}

    /* ------------------------------------------------------------------ */
    /* Skills                                                                */
    /* ------------------------------------------------------------------ */
    .skills-grid {{
      display: flex;
      gap: 24px;
    }}

    .skills-col {{
      flex: 1;
    }}

    .skills-col h4 {{
      font-size: 9.5pt;
      font-weight: 700;
      color: #444;
      margin-bottom: 4px;
    }}

    .skill-tag {{
      display: inline-block;
      background: #eef3fb;
      border: 1px solid #c8d8f0;
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 8.5pt;
      color: #1E3A5F;
      margin: 2px 3px 2px 0;
    }}

    /* ------------------------------------------------------------------ */
    /* Languages                                                             */
    /* ------------------------------------------------------------------ */
    .lang-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .lang-item {{
      font-size: 9.5pt;
      color: #333;
    }}

    .lang-item .lang-level {{
      color: #888;
      font-size: 9pt;
    }}

    /* ------------------------------------------------------------------ */
    /* Extra                                                                  */
    /* ------------------------------------------------------------------ */
    .extra-projects {{
      font-size: 9pt;
      color: #1E3A5F;
      margin-bottom: 4px;
    }}

    .extra-hobbies {{
      font-size: 9pt;
      color: #333;
    }}

    /* ------------------------------------------------------------------ */
    /* Links                                                                 */
    /* ------------------------------------------------------------------ */
    a {{
      color: #1E3A5F;
      text-decoration: none;
    }}
  </style>
</head>
<body>

  <!-- ================================================================== -->
  <!-- HEADER                                                               -->
  <!-- ================================================================== -->
  <div class="header">
    <h1>{name}</h1>
    <div class="meta">
      {city_span}
      {phone_span}
      {email_span}
      {links_spans}
    </div>
    {about_block}
  </div>

  <!-- ================================================================== -->
  <!-- EDUCATION                                                            -->
  <!-- ================================================================== -->
  {education_block}

  <!-- ================================================================== -->
  <!-- EXPERIENCE                                                           -->
  <!-- ================================================================== -->
  {experience_block}

  <!-- ================================================================== -->
  <!-- SKILLS                                                               -->
  <!-- ================================================================== -->
  {skills_block}

  <!-- ================================================================== -->
  <!-- LANGUAGES                                                            -->
  <!-- ================================================================== -->
  {languages_block}

  <!-- ================================================================== -->
  <!-- EXTRA                                                                -->
  <!-- ================================================================== -->
  {extra_block}

</body>
</html>
"""


def _safe(value, default: str = "") -> str:
    """Return str(value) or default if value is None/empty."""
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _esc(text: str) -> str:
    """Basic HTML escaping for injected text content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_personal(personal: dict) -> dict:
    """Return substitution fragments for the header block."""
    name = _esc(_safe(personal.get("name"), "Без имени"))
    city = _safe(personal.get("city"))
    phone = _safe(personal.get("phone"))
    email = _safe(personal.get("email"))
    links: list = personal.get("links") or []
    about = _safe(personal.get("about"))

    city_span = f"<span>{_esc(city)}</span>" if city else ""
    phone_span = f"<span>{_esc(phone)}</span>" if phone else ""
    email_span = f'<span><a href="mailto:{_esc(email)}">{_esc(email)}</a></span>' if email else ""

    links_spans = ""
    for link in links:
        link_s = _safe(link)
        if link_s:
            links_spans += f'<span><a href="{_esc(link_s)}">{_esc(link_s)}</a></span>'

    about_block = (
        f'<div class="about">{_esc(about)}</div>' if about else ""
    )

    return {
        "name": name,
        "city_span": city_span,
        "phone_span": phone_span,
        "email_span": email_span,
        "links_spans": links_spans,
        "about_block": about_block,
    }


def _build_education(education: list) -> str:
    if not education:
        return ""
    items_html = ""
    for edu in education:
        university = _esc(_safe(edu.get("university")))
        faculty = _esc(_safe(edu.get("faculty")))
        speciality = _esc(_safe(edu.get("speciality")))
        year = _esc(_safe(edu.get("year")))
        achievements = _esc(_safe(edu.get("achievements")))

        detail_parts = []
        if faculty:
            detail_parts.append(faculty)
        if speciality:
            detail_parts.append(speciality)
        if year:
            detail_parts.append(f"Выпуск {year}")

        detail_str = " &nbsp;·&nbsp; ".join(detail_parts) if detail_parts else ""
        achievements_str = (
            f'<div class="edu-achievements">✦ {achievements}</div>'
            if achievements
            else ""
        )

        items_html += f"""
        <div class="edu-item">
          <div class="edu-name">{university}</div>
          {f'<div class="edu-detail">{detail_str}</div>' if detail_str else ''}
          {achievements_str}
        </div>"""

    return f"""
    <div class="section">
      <div class="section-title">Образование</div>
      {items_html}
    </div>"""


def _build_experience(experience: list) -> str:
    if not experience:
        return ""
    items_html = ""
    for exp in experience:
        title = _esc(_safe(exp.get("title")))
        role = _esc(_safe(exp.get("role")))
        description = _esc(_safe(exp.get("description")))
        result = _esc(_safe(exp.get("result")))

        items_html += f"""
        <div class="exp-item">
          <div class="exp-title">{title}</div>
          {f'<div class="exp-role">{role}</div>' if role else ''}
          {f'<div class="exp-desc">{description}</div>' if description else ''}
          {f'<div class="exp-result">Результат: {result}</div>' if result else ''}
        </div>"""

    return f"""
    <div class="section">
      <div class="section-title">Опыт и проекты</div>
      {items_html}
    </div>"""


def _build_skills(skills: dict) -> str:
    if not skills:
        return ""
    hard: list = skills.get("hard") or []
    soft: list = skills.get("soft") or []
    if not hard and not soft:
        return ""

    hard_tags = "".join(
        f'<span class="skill-tag">{_esc(str(s))}</span>' for s in hard
    )
    soft_tags = "".join(
        f'<span class="skill-tag">{_esc(str(s))}</span>' for s in soft
    )

    hard_col = (
        f'<div class="skills-col"><h4>Hard skills</h4>{hard_tags}</div>'
        if hard
        else ""
    )
    soft_col = (
        f'<div class="skills-col"><h4>Soft skills</h4>{soft_tags}</div>'
        if soft
        else ""
    )

    return f"""
    <div class="section">
      <div class="section-title">Навыки</div>
      <div class="skills-grid">
        {hard_col}
        {soft_col}
      </div>
    </div>"""


def _build_languages(languages: list) -> str:
    if not languages:
        return ""
    items = ""
    for lang in languages:
        language = _esc(_safe(lang.get("language")))
        level = _esc(_safe(lang.get("level")))
        if language:
            level_part = f' <span class="lang-level">({level})</span>' if level else ""
            items += f'<div class="lang-item">{language}{level_part}</div>'

    if not items:
        return ""

    return f"""
    <div class="section">
      <div class="section-title">Языки</div>
      <div class="lang-list">{items}</div>
    </div>"""


def _build_extra(extra: dict) -> str:
    if not extra:
        return ""
    projects: list = extra.get("projects") or []
    hobbies = _safe(extra.get("hobbies"))
    if not projects and not hobbies:
        return ""

    projects_html = ""
    if projects:
        project_links = ""
        for p in projects:
            p_s = _safe(p)
            if p_s:
                project_links += f'<div class="extra-projects"><a href="{_esc(p_s)}">{_esc(p_s)}</a></div>'
        if project_links:
            projects_html = f"<div><strong>Проекты:</strong><br>{project_links}</div>"

    hobbies_html = (
        f'<div class="extra-hobbies"><strong>Хобби:</strong> {_esc(hobbies)}</div>'
        if hobbies
        else ""
    )

    return f"""
    <div class="section">
      <div class="section-title">Дополнительно</div>
      {projects_html}
      {hobbies_html}
    </div>"""


def generate_pdf(resume_data: dict) -> bytes:
    """
    Render *resume_data* (matching the ResumeData JSON schema from the brief)
    into an A4-sized PDF and return the raw PDF bytes.
    """
    personal: dict = resume_data.get("personal") or {}
    education: list = resume_data.get("education") or []
    experience: list = resume_data.get("experience") or []
    skills: dict = resume_data.get("skills") or {}
    languages: list = resume_data.get("languages") or []
    extra: dict = resume_data.get("extra") or {}

    personal_parts = _build_personal(personal)
    education_block = _build_education(education)
    experience_block = _build_experience(experience)
    skills_block = _build_skills(skills)
    languages_block = _build_languages(languages)
    extra_block = _build_extra(extra)

    html_content = HTML_TEMPLATE.format(
        **personal_parts,
        education_block=education_block,
        experience_block=experience_block,
        skills_block=skills_block,
        languages_block=languages_block,
        extra_block=extra_block,
    )

    return _render_pdf(html_content)
