from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from openai import OpenAI
from sqlalchemy.orm import Session as DBSession

from app import models

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-5"  # NEVER change this

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """\
Ты — карьерный консультант. Твоя задача — собрать данные кандидата для составления резюме под конкретную вакансию.

Вакансия: {vacancy_text}
Ключевые требования вакансии: {vacancy_requirements}

Постоянные данные кандидата (уже известны, НЕ спрашивай их повторно):
{user_profile}

{github_context}

АЛГОРИТМ:
1. НЕ приветствуй — кандидат уже видел вводное сообщение. Сразу задавай первый вопрос.
2. Задавай строго по ОДНОМУ вопросу за раз.
3. Порядок сбора данных:
   - Опыт: проекты, хакатоны, чемпионаты, стажировки — всё что не указано в профиле
   - Навыки — только те, что важны для ЭТОЙ вакансии
   - Уточняй цифры: "Какое место заняли?", "Что именно делал?", "Какой результат?"
   - Хобби, дополнительные ссылки — в конце
4. Когда все данные собраны — скажи пользователю что готов генерировать.
   Верни JSON: {{"status": "complete", "data": {{<все собранные данные>}}}}

СТИЛЬ: дружелюбный, конкретный, без воды. Не задавай несколько вопросов сразу.
ВАЖНО: НЕ выдумывай данные (курсы, предметы, достижения). Используй ТОЛЬКО то, что сказал кандидат.\
"""

GENERATE_PROMPT = """\
Ты — профессиональный HR-консультант и карьерный коуч. Составь идеальное резюме для стажировки.

ВХОДНЫЕ ДАННЫЕ:
- Описание вакансии: {vacancy_text}
- Постоянные данные кандидата: {user_profile}
- Дополнительные данные из диалога: {candidate_data}

ИНСТРУКЦИИ:
1. Проанализируй вакансию: выдели ключевые требования, hard skills, soft skills.
2. Составь резюме строго по JSON-структуре ниже.
3. Используй глаголы действия: "разработал", "оптимизировал", "реализовал", "повысил".
4. Добавляй цифры и результаты везде, где они есть.
5. Если данных не хватает — используй учебные проекты или ставь "—".
6. Hard skills — только те, что релевантны вакансии.
7. Раздел "about" — кто кандидат, что умеет, какую пользу принесёт компании.
8. Опыт — от самого релевантного к наименее.
9. IT-вакансия → акцент на технических навыках. Бизнес → акцент на софт-скиллах.

БАЛАНС РЕАЛЬНОСТЬ / ТВОРЧЕСТВО:
Строго фактическое (80%) — НЕ выдумывать:
  имена, даты, места в чемпионатах, названия компаний / вузов, конкретные цифры,
  технологии не упомянутые кандидатом, названия курсов и сертификатов.

Допустимое обогащение (~20%) — только то, что нельзя проверить фактически:
  • Стиль и глаголы: усиляй формулировки ("участвовал" → "разработал совместно с командой"),
    добавляй профессиональные глаголы действия.
  • Общие soft skills ("ответственность", "инициативность", "обучаемость") — если вписываются
    в контекст.
  • Краткое описание роли в проекте — если кандидат упомянул проект, но не описал детали.

Главное правило: не добавляй ничего, что кандидат мог бы опровергнуть на собеседовании.

ФОРМАТ: верни ТОЛЬКО валидный JSON без markdown-обёртки и пояснений:
{{
  "personal": {{"name": "", "city": "", "phone": "", "email": "", "links": [], "about": ""}},
  "education": [{{"university": "", "faculty": "", "speciality": "", "year": "", "achievements": ""}}],
  "experience": [{{"title": "", "role": "", "description": "", "result": ""}}],
  "skills": {{"hard": [], "soft": []}},
  "languages": [{{"language": "", "level": ""}}],
  "extra": {{"projects": ["строка: URL или название проекта"], "hobbies": ""}}
}}\
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def profile_to_str(profile: models.Profile | None) -> str:
    """Convert a Profile ORM object to a human-readable string for prompt substitution."""
    if profile is None:
        return "Данные профиля не заполнены."

    lines: list[str] = []

    def add(label: str, value: str | None) -> None:
        if value:
            lines.append(f"- {label}: {value}")

    add("Имя", profile.name)
    add("Город", profile.city)
    add("Телефон", profile.phone)
    add("Telegram", profile.telegram)
    add("Email", profile.email)
    add("Ссылка hh.ru", profile.link_hh)
    add("Портфолио / GitHub", profile.link_portfolio)
    try:
        extra_links = json.loads(profile.links or "[]")
        for lnk in extra_links:
            if lnk:
                lines.append(f"- Ссылка: {lnk}")
    except Exception:
        pass
    add("Вуз", profile.university)
    add("Факультет", profile.faculty)
    add("Специальность", profile.speciality)
    add("Год окончания / курс", profile.graduation_year)

    if profile.languages:
        try:
            langs = json.loads(profile.languages)
            if langs:
                lang_str = ", ".join(
                    f"{l.get('language', '')} ({l.get('level', '')})" for l in langs
                )
                lines.append(f"- Языки: {lang_str}")
        except (json.JSONDecodeError, TypeError):
            pass

    return "\n".join(lines) if lines else "Данные профиля не заполнены."


def _fetch_github_context(profile: models.Profile | None) -> str:
    """Fetch real GitHub repo list if profile has a GitHub link."""
    if not profile:
        return ""
    import re
    import requests as _req

    github_url = None
    candidates = [profile.link_portfolio or ""]
    try:
        extra = json.loads(profile.links or "[]")
        candidates += [str(u) for u in extra]
    except Exception:
        pass

    for url in candidates:
        if "github.com" in url:
            github_url = url
            break

    if not github_url:
        return ""

    m = re.search(r"github\.com/([^/?#]+)", github_url)
    if not m:
        return ""
    username = m.group(1)

    try:
        resp = _req.get(
            f"https://api.github.com/users/{username}/repos?per_page=20&sort=updated",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=5,
        )
        if resp.status_code == 200:
            repos = resp.json()
            names = [r["name"] for r in repos if r.get("name") and not r.get("fork")][:12]
            if names:
                return f"Реальные репозитории GitHub кандидата ({username}): {', '.join(names)}\nИспользуй эти названия в резюме — они реальные."
    except Exception:
        pass
    return ""


def _extract_vacancy_requirements(vacancy_text: str) -> str:
    """
    Very lightweight extraction: return the first 600 characters of the vacancy text
    as a rough stand-in for the requirements.  The AI model itself will do the proper
    analysis inside its context window.
    """
    if not vacancy_text:
        return "Не указаны."
    return vacancy_text[:600]


def _strip_markdown_json(text: str) -> str:
    """Remove markdown code fences that the model may wrap around JSON output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove the opening fence (e.g. ```json or just ```)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove the closing fence
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat_response(session_id: str, user_message: str, db: DBSession) -> dict:
    """
    Handle one turn of the candidate interview chat.

    Steps:
      1. Load session (404 if missing).
      2. Load profile for the session's owner.
      3. Persist the user message.
      4. Build the messages list (system + history).
      5. Call OpenAI.
      6. Persist the assistant reply.
      7. Detect completion marker and flip session.is_complete.
      8. Return {reply, is_complete}.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == session.user_id)
        .first()
    )

    # Persist user message first
    user_msg_obj = models.Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=user_message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg_obj)
    db.commit()

    # Build history
    history = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    vacancy_text = session.vacancy_text or "Описание вакансии не предоставлено."
    vacancy_requirements = _extract_vacancy_requirements(vacancy_text)
    user_profile_str = profile_to_str(profile)
    github_context = _fetch_github_context(profile)

    system_content = CHAT_SYSTEM_PROMPT.format(
        vacancy_text=vacancy_text,
        vacancy_requirements=vacancy_requirements,
        user_profile=user_profile_str,
        github_context=github_context,
    )

    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    reply_text: str = completion.choices[0].message.content or ""

    # Persist assistant reply
    assistant_msg_obj = models.Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=reply_text,
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg_obj)

    # Detect completion
    is_complete = False
    if '"status": "complete"' in reply_text or '"status":"complete"' in reply_text:
        is_complete = True
        session.is_complete = True

    db.commit()

    return {"reply": reply_text, "is_complete": is_complete}


def generate_resume(session_id: str, db: DBSession) -> models.Resume:
    """
    Generate a structured resume JSON for the given session.

    Steps:
      1. Load session.
      2. Load profile.
      3. Collect candidate_data from the last assistant message with complete status,
         or fall back to all assistant messages concatenated.
      4. Call OpenAI with the generation prompt.
      5. Parse JSON from the response.
      6. Persist and return a Resume record.
    """
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == session.user_id)
        .first()
    )

    # Gather candidate data from the conversation
    all_messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    candidate_data_str = ""
    # Prefer the last assistant message that contains the "complete" JSON blob
    for msg in reversed(all_messages):
        if msg.role == "assistant" and (
            '"status": "complete"' in msg.content
            or '"status":"complete"' in msg.content
        ):
            try:
                # Extract the JSON portion
                start = msg.content.find("{")
                end = msg.content.rfind("}") + 1
                if start != -1 and end > start:
                    blob = json.loads(msg.content[start:end])
                    candidate_data_str = json.dumps(
                        blob.get("data", blob), ensure_ascii=False, indent=2
                    )
            except (json.JSONDecodeError, ValueError):
                candidate_data_str = msg.content
            break

    if not candidate_data_str:
        # Fallback: concatenate all assistant messages
        assistant_texts = [m.content for m in all_messages if m.role == "assistant"]
        candidate_data_str = "\n".join(assistant_texts) or "Данные не предоставлены."

    vacancy_text = session.vacancy_text or "Описание вакансии не предоставлено."
    user_profile_str = profile_to_str(profile)

    prompt = GENERATE_PROMPT.format(
        vacancy_text=vacancy_text,
        user_profile=user_profile_str,
        candidate_data=candidate_data_str,
    )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_response: str = completion.choices[0].message.content or "{}"
    clean_json = _strip_markdown_json(raw_response)

    try:
        resume_data = json.loads(clean_json)
    except json.JSONDecodeError:
        # Attempt a second strip in case there were extra characters
        start = clean_json.find("{")
        end = clean_json.rfind("}") + 1
        if start != -1 and end > start:
            try:
                resume_data = json.loads(clean_json[start:end])
            except json.JSONDecodeError:
                resume_data = {"raw": raw_response}
        else:
            resume_data = {"raw": raw_response}

    # Derive vacancy_title
    vacancy_title: str | None = None
    if session.vacancy_summary:
        vacancy_title = session.vacancy_summary
    elif vacancy_text and vacancy_text != "Описание вакансии не предоставлено.":
        first_line = vacancy_text.split("\n")[0].strip()
        vacancy_title = first_line[:120] if first_line else None

    # Derive vacancy_preview (first 100 chars of vacancy_text)
    vacancy_preview: str | None = None
    if vacancy_text and vacancy_text != "Описание вакансии не предоставлено.":
        vacancy_preview = vacancy_text[:100]

    resume_record = models.Resume(
        id=str(uuid.uuid4()),
        user_id=session.user_id,
        session_id=session_id,
        vacancy_title=vacancy_title,
        vacancy_preview=vacancy_preview,
        data=json.dumps(resume_data, ensure_ascii=False),
        created_at=datetime.utcnow(),
    )
    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)

    return resume_record
