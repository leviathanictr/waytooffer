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

{profile_context}

АЛГОРИТМ:
1. НЕ приветствуй — кандидат уже видел вводное сообщение.
2. СНАЧАЛА (до вопросов): если в profile_context есть GitHub-репозитории, ссылки или данные по вузу —
   кратко сообщи что нашёл и спроси, стоит ли включить конкретные находки в резюме.
   Например: "Вижу у тебя на GitHub проект waytooffer — хочешь упомянуть его?"
   Если ничего не найдено — сразу переходи к вопросам.
3. Задавай строго по ОДНОМУ вопросу за раз.
4. Порядок сбора данных:
   - Опыт: проекты, хакатоны, чемпионаты, стажировки
   - Навыки — только те, что важны для ЭТОЙ вакансии
   - Уточняй детали: "Какой результат?", "Что именно делал?", "Какие технологии?"
   - Хобби, дополнительные ссылки — в конце
5. ЗАВЕРШЕНИЕ ДИАЛОГА — СТРОГО ОБЯЗАТЕЛЬНО:
   Если кандидат говорит "генерируй", "делай резюме", "готово", "хватит", "всё", "давай", "создай" —
   ИЛИ ты сам считаешь что собрал достаточно данных —
   верни ТОЛЬКО этот JSON (никакого другого текста, никакого резюме текстом, никаких вводных):
   {{"status": "complete", "data": {{<все собранные данные в свободном формате>}}}}
   ЗАПРЕЩЕНО: делать текстовое резюме, подводить итоги, задавать уточняющие вопросы после этого момента.

ПОЛИТИКА ЭФФЕКТИВНОСТИ (главное правило):
Твоя цель — максимально сильное резюме, а не нотариальное заверение фактов.
- МОЖНО и НУЖНО предлагать сильные формулировки, усиливать глаголы, добавлять трудно проверяемые детали.
- Если кандидат просит добавить впечатляющий опыт — ПОМОГАЙ, не отказывай. Просто всегда добавляй в конце
  пометку: "(легко проверить)" или "(сложно проверить)".
  "(легко проверить)" — конкретные даты, названия компаний, места в конкурсах, точные числа.
  "(сложно проверить)" — описание роли, инициативы, soft skills, вклад в обсуждения, общие результаты.
- НЕЛЬЗЯ выдумывать: точные даты, названия компаний/вузов, места в соревнованиях, которые кандидат не называл.
- Никогда не говори "я должен быть честным" или "не могу добавить это" — просто оцени риск.

СТИЛЬ: дружелюбный, конкретный, без воды. Не задавай несколько вопросов сразу.\
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
5. Если данных для поля нет — НЕ пиши "—", НЕ пиши "null", НЕ пиши "не указано".
   Используй пустую строку "" или пустой массив []. Лучше пропустить поле, чем ставить прочерк.
6. Hard skills — только те, что релевантны вакансии.
7. Раздел "about" — кто кандидат, что умеет, какую пользу принесёт компании.
8. Опыт — от самого релевантного к наименее.
9. IT-вакансия → акцент на технических навыках. Бизнес → акцент на софт-скиллах.

БАЛАНС РЕАЛЬНОСТЬ / ТВОРЧЕСТВО:
Нельзя выдумывать (легко проверить):
  конкретные даты, названия компаний/вузов, места в чемпионатах, точные числа, которые кандидат не называл.

Свободно обогащай (пиши уверенно, это норма для резюме):
  • Усиляй глаголы: "участвовал" → "разработал совместно с командой", "помогал" → "реализовал"
  • Все уместные soft skills из контекста — добавляй без ограничений
  • Если кандидат назвал проект — опиши что МОГ делать специалист такого уровня в таком проекте
  • Общие результаты без точных цифр: "улучшил производительность", "оптимизировал процесс"
  • Курсы вуза из учебной программы — если специальность известна, добавь типичные дисциплины

ТИПОГРАФИКА: всегда ставь дефис между латинскими словами/аббревиатурами и русскими словами.
Правильно: "Frontend-разработчик", "SQL-запрос", "A/B-тест", "push-уведомление", "BI-дашборд", "RFM-сегментация", "full-stack".
НИКОГДА не пиши слитно: "Frontendразработчик", "SQLзапрос", "A/Bтест" — это грубая ошибка.

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


def _safe_format(template: str, **kwargs) -> str:
    """Format template safely even when values contain curly braces (e.g. JSON)."""
    _L = "\x00LB\x00"
    _R = "\x00RB\x00"
    result = template.replace("{{", _L).replace("}}", _R)
    for k, v in kwargs.items():
        result = result.replace("{" + k + "}", str(v))
    return result.replace(_L, "{").replace(_R, "}")


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


def _fetch_portfolio_context(profile: models.Profile | None) -> str:
    """Try to fetch useful text from non-GitHub portfolio links."""
    if not profile:
        return ""
    import re
    import requests as _req

    urls: list[str] = []
    if profile.link_portfolio and "github.com" not in (profile.link_portfolio or "").lower():
        urls.append(profile.link_portfolio)
    try:
        for lnk in json.loads(profile.links or "[]"):
            if lnk and "github.com" not in str(lnk).lower():
                urls.append(str(lnk))
    except Exception:
        pass

    results: list[str] = []
    for url in urls[:2]:
        try:
            resp = _req.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4, allow_redirects=True)
            if resp.status_code == 200:
                text = re.sub(r"<[^>]+>", " ", resp.text)
                text = re.sub(r"\s+", " ", text).strip()[:600]
                if len(text) > 50:
                    results.append(f"Содержимое сайта {url}:\n{text}")
        except Exception:
            pass
    return "\n".join(results)


def _fetch_university_context(profile: models.Profile | None) -> str:
    """Search for course list of the user's university speciality."""
    if not profile:
        return ""
    university = (profile.university or "").strip()
    speciality = (profile.speciality or "").strip()
    faculty = (profile.faculty or "").strip()
    if not university:
        return ""

    import re
    import requests as _req

    query = f"{university} {faculty} {speciality} учебный план дисциплины курсы программа"
    try:
        resp = _req.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "ru-ru"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; ResumeBot/1.0)", "Accept-Language": "ru-RU,ru;q=0.9"},
            timeout=6,
        )
        if resp.status_code == 200:
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            clean = [re.sub(r"<[^>]+>", "", s).strip() for s in snippets[:4] if s.strip()]
            clean = [c for c in clean if len(c) > 30][:3]
            if clean:
                label = f"«{speciality}»" if speciality else f"«{faculty}»" if faculty else ""
                return (
                    f"Программа {label} в «{university}» (из поиска):\n"
                    + "\n".join(clean)
                    + "\nУточни у кандидата, какие из этих курсов он прошёл или проходит сейчас."
                )
    except Exception:
        pass
    return ""


def _fetch_full_profile_context(profile: models.Profile | None) -> str:
    """Combine GitHub repos + portfolio + university context into one string."""
    parts: list[str] = []
    gh = _fetch_github_context(profile)
    if gh:
        parts.append(gh)
    pf = _fetch_portfolio_context(profile)
    if pf:
        parts.append(pf)
    uni = _fetch_university_context(profile)
    if uni:
        parts.append(uni)
    return "\n\n".join(parts)


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

def generate_resume_threaded(session_id: str, job: object) -> None:
    """Run resume generation in a background thread, storing result in *job*."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        resume = generate_resume(session_id, db)
        # Convert ORM object to dict for the job result
        import json as _json
        data_dict: dict = {}
        try:
            data_dict = _json.loads(resume.data)
        except Exception:
            pass
        result = {
            "resume_id": resume.id,
            "session_id": resume.session_id,
            "data": data_dict,
            "pdf_url": f"/resume/{resume.id}/pdf",
            "created_at": resume.created_at.isoformat() if resume.created_at else None,
        }
        job.finish(is_complete=True, result=result)  # type: ignore[attr-defined]
    except Exception as e:
        job.fail(str(e))  # type: ignore[attr-defined]
    finally:
        db.close()


def chat_response_threaded(session_id: str, user_message: str, job: object) -> None:
    """Run the chat completion in a background thread, updating *job* in place."""
    from app.database import SessionLocal
    from app import jobs as _jobs  # noqa: F401 — type hint only
    db = SessionLocal()
    try:
        session = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session is None:
            job.fail("Session not found")
            return

        profile = (
            db.query(models.Profile)
            .filter(models.Profile.user_id == session.user_id)
            .first()
        )

        user_msg_obj = models.Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=user_message,
            created_at=datetime.utcnow(),
        )
        db.add(user_msg_obj)
        db.commit()

        history = (
            db.query(models.Message)
            .filter(models.Message.session_id == session_id)
            .order_by(models.Message.created_at)
            .all()
        )

        system_content = _safe_format(
            CHAT_SYSTEM_PROMPT,
            vacancy_text=session.vacancy_text or "",
            vacancy_requirements=_extract_vacancy_requirements(session.vacancy_text or ""),
            user_profile=profile_to_str(profile),
            profile_context=_fetch_full_profile_context(profile),
        )

        messages = [{"role": "system", "content": system_content}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        full_reply = ""
        try:
            stream = client.chat.completions.create(model=MODEL, messages=messages, stream=True)
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_reply += delta
                    job.append(delta)
        except Exception as e:
            job.fail(str(e))
            return

        is_complete = '"status": "complete"' in full_reply or '"status":"complete"' in full_reply

        assistant_msg = models.Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=full_reply,
            created_at=datetime.utcnow(),
        )
        db.add(assistant_msg)
        if is_complete:
            session.is_complete = True
            # Clear the streamed JSON from job content so the frontend
            # never sees the raw {"status":"complete",...} blob.
            with job._lock:
                job.content = ""
        db.commit()

        job.finish(is_complete)
    except Exception as e:
        job.fail(str(e))
    finally:
        db.close()


def chat_response_stream(session_id: str, user_message: str, db: DBSession):
    """Streaming version — yields SSE lines, then finalizes DB."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        yield 'data: {"error": "Session not found"}\n\n'
        return

    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == session.user_id)
        .first()
    )

    user_msg_obj = models.Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=user_message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg_obj)
    db.commit()

    history = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
        .all()
    )

    system_content = CHAT_SYSTEM_PROMPT.format(
        vacancy_text=session.vacancy_text or "",
        vacancy_requirements=_extract_vacancy_requirements(session.vacancy_text or ""),
        user_profile=profile_to_str(profile),
        github_context=_fetch_github_context(profile),
    )

    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    full_reply = ""
    try:
        stream = client.chat.completions.create(model=MODEL, messages=messages, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    is_complete = '"status": "complete"' in full_reply or '"status":"complete"' in full_reply

    assistant_msg = models.Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=full_reply,
        created_at=datetime.utcnow(),
    )
    db.add(assistant_msg)
    if is_complete:
        session.is_complete = True
    db.commit()

    yield f"data: {json.dumps({'done': True, 'is_complete': is_complete})}\n\n"


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

    system_content = _safe_format(
        CHAT_SYSTEM_PROMPT,
        vacancy_text=vacancy_text,
        vacancy_requirements=vacancy_requirements,
        user_profile=user_profile_str,
        profile_context=_fetch_full_profile_context(profile),
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

    prompt = _safe_format(
        GENERATE_PROMPT,
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
