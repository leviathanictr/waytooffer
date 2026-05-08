from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Shared / nested
# ---------------------------------------------------------------------------

class LanguageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: str
    level: str


# ---------------------------------------------------------------------------
# Auth — requests
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    phone: str
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    login: str  # phone or email
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    user_id: str
    code: str


class VerifyPhoneRequest(BaseModel):
    user_id: str
    code: str


class ResendVerificationRequest(BaseModel):
    user_id: str
    type: Literal["email", "phone"]


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    new_password_confirm: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    password: str


class ChangePhoneRequest(BaseModel):
    new_phone: str
    password: str


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    link_hh: Optional[str] = None
    link_portfolio: Optional[str] = None
    university: Optional[str] = None
    faculty: Optional[str] = None
    speciality: Optional[str] = None
    graduation_year: Optional[str] = None
    languages: Optional[List[LanguageItem]] = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    link_hh: Optional[str] = None
    link_portfolio: Optional[str] = None
    university: Optional[str] = None
    faculty: Optional[str] = None
    speciality: Optional[str] = None
    graduation_year: Optional[str] = None
    languages: Optional[List[LanguageItem]] = None


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    vacancy_url: Optional[str] = None
    vacancy_text: Optional[str] = None


class MessageRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    reply: str
    is_complete: bool


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    vacancy_summary: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    vacancy_title: Optional[str] = None
    vacancy_preview: Optional[str] = None
    pdf_url: str
    created_at: datetime


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    session_id: str
    data: dict
    pdf_url: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Auth — responses
# ---------------------------------------------------------------------------

class RegisterResponse(BaseModel):
    user_id: str
    needs_verification: bool = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str


class VerifyResponse(BaseModel):
    success: bool
    message: str
