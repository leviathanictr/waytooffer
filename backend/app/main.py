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
from fastapi.responses import Response
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
    ChangeEmailRequest,
    ChangePasswordRequest,
    ChangePhoneRequest,
    ChatResponse,
    EducationItem,
    LoginRequest,
    MessageRequest,
    ProfileResponse,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
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
    verify_code,
)
from app.ai import chat_response as ai_chat_response
from app.ai import generate_resume as ai_generate_resume
from app.parser import parse_vacancy
from app.pdf import generate_pdf

# Create all tables on startup (models must be imported first so Base knows about them)
Base.metadata.create_all(bind=engine)

# Column migrations for existing tables (safe — ignores already-existing columns)
from sqlalchemy import text as _sql_text
with engine.connect() as _conn:
    for _col in [("links", "TEXT"), ("education_list", "TEXT")]:
        try:
            _conn.execute(_sql_text(f"ALTER TABLE profiles ADD COLUMN {_col[0]} {_col[1]}"))
            _conn.commit()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Resume Builder API", version="1.0.0")

_cors_raw = os.getenv("CORS_ORIGINS", "https://waytooffer.ru")
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
    if body.password != body.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Check uniqueness
    if db.query(models.User).filter(models.User.phone == body.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_id = str(uuid.uuid4())
    user = models.User(
        id=user_id,
        phone=body.phone,
        email=body.email,
        hashed_password=hash_password(body.password),
        email_verified=False,
        phone_verified=True,  # SMS disabled — verified automatically
        created_at=datetime.utcnow(),
    )
    db.add(user)

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
def login(body: LoginRequest, db: DBSession = Depends(get_db)):
    # Determine lookup by email or phone
    if "@" in body.login:
        user = db.query(models.User).filter(models.User.email == body.login).first()
    else:
        user = db.query(models.User).filter(models.User.phone == body.login).first()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.email_verified or not user.phone_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please verify your email and phone number.",
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


@app.post("/auth/change-email", status_code=status.HTTP_200_OK)
def change_email(
    body: ChangeEmailRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect",
        )

    existing = db.query(models.User).filter(models.User.email == body.new_email).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use",
        )

    current_user.email = body.new_email
    db.commit()
    return {"message": "Email changed successfully"}


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


@app.post("/session/{session_id}/message", response_model=ChatResponse)
def send_message(
    session_id: str,
    body: MessageRequest,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    # Verify session belongs to current user
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = ai_chat_response(session_id, body.text, db)
    return ChatResponse(reply=result["reply"], is_complete=result["is_complete"])


@app.post("/session/{session_id}/generate", response_model=ResumeResponse)
def generate_resume_endpoint(
    session_id: str,
    current_user: Annotated[models.User, Depends(get_current_user)],
    db: DBSession = Depends(get_db),
):
    # Verify session belongs to current user
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    resume = ai_generate_resume(session_id, db)
    return _resume_to_response(resume)


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
