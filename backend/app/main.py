from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Annotated, List

from dotenv import load_dotenv

load_dotenv()  # Load .env before anything that reads env-vars

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import threading

from fastapi.responses import Response

from app import jobs as _jobs
from sqlalchemy.orm import Session as DBSession

from app import models
from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import engine, Base, get_db
from app.schemas import (
    AccessTokenResponse,
    ChangeEmailConfirm,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ChangePhoneRequest,
    EducationItem,
    LoginRequest,
    MessageRequest,
    ProfileResponse,
    ProfileUpdate,
    RefreshRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    RequestVerificationRequest,
    RequestVerificationResponse,
    ResendVerificationRequest,
    ResumeListItem,
    ResumeResponse,
    SessionCreate,
    SessionResponse,
    TokenResponse,
    VerifyEmailRequest,
    VerifyPhoneRequest,
    VerifyResponse,
    LanguageItem,
)
from app.verification import (
    create_verification_code,
    send_email_code,
    send_password_reset_email,
    verify_code,
)
from app.ai import chat_response_threaded as ai_chat_response_threaded
from app.ai import generate_resume_threaded as ai_generate_resume_threaded
from app.parser import parse_vacancy
from app.pdf import generate_pdf

# Create all tables on startup (models must be imported first so Base knows about them)
Base.metadata.create_all(bind=engine)

# Column migrations for existing tables
from sqlalchemy import text as _sql_text
with engine.connect() as _conn:
    # Add new Profile columns
    for _col in [("links", "TEXT"), ("education_list", "TEXT"), ("telegram", "TEXT")]:
        try:
            _conn.execute(_sql_text(f"ALTER TABLE profiles ADD COLUMN {_col[0]} {_col[1]}"))
            _conn.commit()
        except Exception:
            pass
    # Make users.phone nullable (SQLite requires table recreation)
    try:
        _info = _conn.execute(_sql_text("PRAGMA table_info(users)")).fetchall()
        _phone = next((r for r in _info if r[1] == "phone"), None)
        if _phone and _phone[3] == 1:  # notnull=1 → need migration
            _conn.execute(_sql_text("""
                CREATE TABLE users_new (
                    id TEXT PRIMARY KEY,
                    phone TEXT UNIQUE,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    phone_verified INTEGER NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL
                )
            """))
            _conn.execute(_sql_text("INSERT INTO users_new SELECT id, phone, email, hashed_password, email_verified, phone_verified, created_at FROM users"))
            _conn.execute(_sql_text("DROP TABLE users"))
            _conn.execute(_sql_text("ALTER TABLE users_new RENAME TO users"))
            _conn.commit()
    except Exception as _e:
        pass

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Resume Builder API", version="1.0.0")

_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


def _profile_to_response(profile: models.Profile) -> ProfileResponse:
    langs = [LanguageItem(**item) for item in _json_list(profile.languages)]
    edu_raw = _json_list(profile.education_list)
    edu_list = [EducationItem(**item) for item in edu_raw]
    links = _json_list(profile.links)
    return ProfileResponse(
        name=profile.name,
        city=profile.city,
        phone=profile.phone,
        telegram=profile.telegram,
        email=profile.email,
        link_hh=profile.link_hh,
        link_portfolio=profile.link_portfolio,
        university=profile.university,
        faculty=profile.faculty,
        speciality=profile.speciality,
        graduation_year=profile.graduation_year,
        languages=langs,
        links=links,
        education_list=edu_list,
    )


def _resume_to_response(resume: models.Resume) -> ResumeResponse:
    data_dict: dict = {}
    try:
        data_dict = json.loads(resume.data)
    except (json.JSONDecodeError, TypeError):
        data_dict = {}
    return ResumeResponse(
        resume_id=resume.id,
        session_id=resume.session_id,
        data=data_dict,
        pdf_url=f"/resume/{resume.id}/pdf",
        created_at=resume.created_at,
    )


def _resume_to_list_item(resume: models.Resume) -> ResumeListItem:
    return ResumeListItem(
        resume_id=resume.id,
        vacancy_title=resume.vacancy_title,
        vacancy_preview=resume.vacancy_preview,
        pdf_url=f"/resume/{resume.id}/pdf",
        created_at=resume.created_at,
    )


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    body.email = body.email.strip().lower()
    if body.password != body.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_id = str(uuid.uuid4())
    user = models.User(
        id=user_id,
        phone=None,
        email=body.email,
        hashed_password=hash_password(body.password),
        email_verified=False,
        phone_verified=True,  # SMS disabled — verified automatically
        created_at=datetime.utcnow(),
    )
    db.add(user)
    # Force INSERT of the user row before adding the child profile so the FK
    # check on profiles.user_id sees an existing parent. Without this flush
    # SQLAlchemy can emit the profile INSERT first inside a single transaction
    # and Postgres raises profiles_user_id_fkey violation.
    db.flush()

    # Create empty profile
    profile = models.Profile(user_id=user_id)
    db.add(profile)

    db.commit()

    # Send email verification code
    email_code = create_verification_code(user_id, "email", db)
    background_tasks.add_task(send_email_code, body.email, email_code)
    # SMS verification disabled (phone_verified=True at creation)

    return RegisterResponse(user_id=user_id, needs_verification=True)


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    from sqlalchemy import func as _func
    user = (
        db.query(models.User)
        .filter(_func.lower(models.User.email) == body.login.strip().lower())
        .first()
    )

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.email_verified or not user.phone_verified:
        # Send a fresh code so the user can complete verification immediately
        # without having to find the resend button. Existing unused codes are
        # invalidated inside create_verification_code so this is idempotent.
        code = create_verification_code(user.id, "email", db)
        background_tasks.add_task(send_email_code, user.email, code)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "not_verified",
                "message": "Account not verified. A fresh code was sent to your email.",
                "user_id": user.id,
            },
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@app.post("/auth/refresh", response_model=AccessTokenResponse)
def refresh_token(body: RefreshRequest, db: DBSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected refresh token",
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return AccessTokenResponse(access_token=create_access_token(user_id))


@app.post("/auth/verify-email", response_model=VerifyResponse)
def verify_email(body: VerifyEmailRequest, db: DBSession = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == body.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_code(body.user_id, "email", body.code, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    user.email_verified = True
    db.commit()
    return VerifyResponse(success=True, message="Email подтверждён")


@app.post("/auth/verify-phone", response_model=VerifyResponse)
def verify_phone(body: VerifyPhoneRequest, db: DBSession = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == body.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_code(body.user_id, "phone", body.code, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    user.phone_verified = True
    db.commit()
    return VerifyResponse(success=True, message="Телефон подтверждён")


@app.post("/auth/request-verification", response_model=RequestVerificationResponse)
def request_verification(
    body: RequestVerificationRequest,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    """Public lookup-by-email so a user can recover the verify flow on a
    fresh device or after clearing localStorage. Returns user_id (which the
    frontend stores so /verify can submit the code) and triggers a fresh
    email code. Always 404s on unknown email so we don't enumerate accounts."""
    from sqlalchemy import func as _func
    email = body.email.strip().lower()
    user = (
        db.query(models.User)
        .filter(_func.lower(models.User.email) == email)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account for this email")

    if user.email_verified and user.phone_verified:
        return RequestVerificationResponse(
            success=True, user_id=user.id, message="Аккаунт уже подтверждён",
        )

    code = create_verification_code(user.id, "email", db)
    background_tasks.add_task(send_email_code, user.email, code)
    return RequestVerificationResponse(
        success=True, user_id=user.id, message="Код отправлен на email",
    )


@app.post("/auth/resend-verification", response_model=VerifyResponse)
def resend_verification(body: ResendVerificationRequest, background_tasks: BackgroundTasks, db: DBSession = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == body.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    code = create_verification_code(body.user_id, body.type, db)

    if body.type == "email":
        background_tasks.add_task(send_email_code, user.email, code)
    # SMS disabled — phone is auto-verified; ignore resend requests for phone

    return VerifyResponse(success=True, message="Код отправлен на email")


@app.post("/auth/password-reset/request", response_model=VerifyResponse)
def password_reset_request(
    body: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    """Step 1 of password recovery: email -> code. Always responds 200 with the
    same message regardless of whether the account exists, so attackers can't
    enumerate registered emails."""
    from sqlalchemy import func as _func
    email = body.email.strip().lower()
    user = (
        db.query(models.User)
        .filter(_func.lower(models.User.email) == email)
        .first()
    )
    if user is not None:
        code = create_verification_code(user.id, "password_reset", db)
        background_tasks.add_task(send_password_reset_email, user.email, code)
    return VerifyResponse(
        success=True,
        message="Если аккаунт существует — код выслан на email",
    )


@app.post("/auth/password-reset/confirm", response_model=VerifyResponse)
def password_reset_confirm(body: PasswordResetConfirm, db: DBSession = Depends(get_db)):
    """Step 2: validate code + set new password. Receiving the code proves
    control of the inbox, so we also mark email_verified=True — this rescues
    users who were stuck in the unverified-and-forgot-password corner."""
    from sqlalchemy import func as _func
    if body.new_password != body.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )
    email = body.email.strip().lower()
    user = (
        db.query(models.User)
        .filter(_func.lower(models.User.email) == email)
        .first()
    )
    if user is None or not verify_code(user.id, "password_reset", body.code, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или просроченный код",
        )

    user.hashed_password = hash_password(body.new_password)
    user.email_verified = True
    db.commit()
    return VerifyResponse(success=True, message="Пароль изменён, войдите с новым")


@app.post("/auth/change-password", status_code=status.HTTP_200_OK)
def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect",
        )
    if body.new_password != body.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match",
        )

    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@app.post("/auth/change-email/request", status_code=status.HTTP_200_OK)
def change_email_request(
    body: ChangeEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")

    existing = db.query(models.User).filter(models.User.email == body.new_email).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")

    # Store new email in the verification type so confirm can validate it
    code = create_verification_code(current_user.id, f"email_change:{body.new_email}", db)
    background_tasks.add_task(send_email_code, body.new_email, code)
    return {"message": "Код отправлен на новый email"}


@app.post("/auth/change-email/confirm", status_code=status.HTTP_200_OK)
def change_email_confirm(
    body: ChangeEmailConfirm,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    if not verify_code(current_user.id, f"email_change:{body.new_email}", body.code, db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный или просроченный код")

    current_user.email = body.new_email
    db.commit()
    return {"message": "Email успешно изменён"}


@app.post("/auth/change-phone", status_code=status.HTTP_200_OK)
def change_phone(
    body: ChangePhoneRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect",
        )

    existing = db.query(models.User).filter(models.User.phone == body.new_phone).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already in use",
        )

    current_user.phone = body.new_phone
    db.commit()
    return {"message": "Phone changed successfully"}


# ---------------------------------------------------------------------------
# PROFILE
# ---------------------------------------------------------------------------

@app.get("/profile", response_model=ProfileResponse)
def get_profile(
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        # Auto-create if missing (defensive)
        profile = models.Profile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _profile_to_response(profile)


@app.put("/profile", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        profile = models.Profile(user_id=current_user.id)
        db.add(profile)

    if body.name is not None:
        profile.name = body.name
    if body.city is not None:
        profile.city = body.city
    if body.phone is not None:
        profile.phone = body.phone
    if body.telegram is not None:
        profile.telegram = body.telegram
    if body.email is not None:
        profile.email = body.email
    if body.link_hh is not None:
        profile.link_hh = body.link_hh
    if body.link_portfolio is not None:
        profile.link_portfolio = body.link_portfolio
    if body.university is not None:
        profile.university = body.university
    if body.faculty is not None:
        profile.faculty = body.faculty
    if body.speciality is not None:
        profile.speciality = body.speciality
    if body.graduation_year is not None:
        profile.graduation_year = body.graduation_year
    if body.languages is not None:
        profile.languages = json.dumps(
            [lang.model_dump() for lang in body.languages], ensure_ascii=False
        )
    if body.links is not None:
        profile.links = json.dumps(body.links, ensure_ascii=False)
    if body.education_list is not None:
        profile.education_list = json.dumps(
            [edu.model_dump() for edu in body.education_list], ensure_ascii=False
        )

    db.commit()
    db.refresh(profile)
    return _profile_to_response(profile)


# ---------------------------------------------------------------------------
# SESSION
# ---------------------------------------------------------------------------

@app.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    if not body.vacancy_url and not body.vacancy_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either vacancy_url or vacancy_text",
        )

    vacancy_text: str | None = body.vacancy_text
    vacancy_url: str | None = body.vacancy_url
    vacancy_summary: str | None = None

    if body.vacancy_url:
        parsed = parse_vacancy(body.vacancy_url)
        if parsed.get("text"):
            if body.vacancy_text:
                vacancy_text = body.vacancy_text + "\n\n" + parsed["text"]
            else:
                vacancy_text = parsed["text"]
        vacancy_summary = parsed.get("title") or None

    session_id = str(uuid.uuid4())
    session = models.Session(
        id=session_id,
        user_id=current_user.id,
        vacancy_url=vacancy_url,
        vacancy_text=vacancy_text,
        vacancy_summary=vacancy_summary,
        is_complete=False,
        created_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionResponse(
        session_id=session.id,
        vacancy_summary=session.vacancy_summary,
        created_at=session.created_at,
    )


@app.post("/session/{session_id}/message")
def send_message(
    session_id: str,
    body: MessageRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    job_id, job = _jobs.create()
    t = threading.Thread(
        target=ai_chat_response_threaded,
        args=(session_id, body.text, job),
        daemon=True,
    )
    t.start()
    return {"job_id": job_id}


@app.get("/session/{session_id}/poll/{job_id}")
def poll_message(
    session_id: str,
    job_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job.snapshot()


@app.post("/session/{session_id}/generate")
def generate_resume_endpoint(
    session_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    job_id, job = _jobs.create()
    t = threading.Thread(
        target=ai_generate_resume_threaded,
        args=(session_id, job),
        daemon=True,
    )
    t.start()
    return {"job_id": job_id}


@app.get("/session/{session_id}/generate-poll/{job_id}")
def generate_poll(
    session_id: str,
    job_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job.snapshot()


# ---------------------------------------------------------------------------
# RESUME
# ---------------------------------------------------------------------------

@app.get("/resume", response_model=List[ResumeListItem])
def list_resumes(
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    resumes = (
        db.query(models.Resume)
        .filter(models.Resume.user_id == current_user.id)
        .order_by(models.Resume.created_at.desc())
        .all()
    )
    return [_resume_to_list_item(r) for r in resumes]


@app.get("/resume/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    resume = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return _resume_to_response(resume)


@app.get("/resume/{resume_id}/pdf")
def download_resume_pdf(
    resume_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    resume = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    if resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        data_dict: dict = json.loads(resume.data)
    except (json.JSONDecodeError, TypeError):
        data_dict = {}

    pdf_bytes = generate_pdf(data_dict)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="resume.pdf"'},
    )
