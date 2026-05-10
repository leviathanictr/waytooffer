from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    phone = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # "email" or "phone"
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)


class Profile(Base):
    __tablename__ = "profiles"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    name = Column(String, nullable=True)
    city = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    link_hh = Column(String, nullable=True)
    link_portfolio = Column(String, nullable=True)
    university = Column(String, nullable=True)
    faculty = Column(String, nullable=True)
    speciality = Column(String, nullable=True)
    graduation_year = Column(String, nullable=True)
    languages = Column(Text, nullable=True)       # JSON: [{language, level}]
    links = Column(Text, nullable=True)           # JSON: ["url", ...]
    education_list = Column(Text, nullable=True)  # JSON: [{university, faculty, speciality, year, achievements}]


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    vacancy_url = Column(String, nullable=True)
    vacancy_text = Column(Text, nullable=True)
    vacancy_summary = Column(String, nullable=True)
    is_complete = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    vacancy_title = Column(String, nullable=True)
    vacancy_preview = Column(String, nullable=True)
    data = Column(Text, nullable=False)  # JSON string of ResumeData
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
