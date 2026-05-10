from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

import requests
from sqlalchemy.orm import Session as DBSession

from app import models

SMSC_API_URL = "https://smsc.ru/sys/send.php"


def generate_code() -> str:
    return str(secrets.randbelow(900000) + 100000)


def create_verification_code(user_id: str, type_: str, db: DBSession) -> str:
    import uuid

    old_codes = (
        db.query(models.VerificationCode)
        .filter(
            models.VerificationCode.user_id == user_id,
            models.VerificationCode.type == type_,
            models.VerificationCode.used == False,  # noqa: E712
        )
        .all()
    )
    for old in old_codes:
        old.used = True

    code = generate_code()
    new_code = models.VerificationCode(
        id=str(uuid.uuid4()),
        user_id=user_id,
        type=type_,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        used=False,
    )
    db.add(new_code)
    db.commit()
    return code


def verify_code(user_id: str, type_: str, code: str, db: DBSession) -> bool:
    now = datetime.utcnow()
    record = (
        db.query(models.VerificationCode)
        .filter(
            models.VerificationCode.user_id == user_id,
            models.VerificationCode.type == type_,
            models.VerificationCode.code == code,
            models.VerificationCode.used == False,  # noqa: E712
            models.VerificationCode.expires_at > now,
        )
        .first()
    )
    if record is None:
        return False

    record.used = True
    db.commit()
    return True


def _smsc_credentials() -> tuple[str, str] | None:
    """Return (login, password) from env, or None if not configured."""
    login = os.getenv("SMSC_LOGIN", "").strip()
    password = os.getenv("SMSC_PASSWORD", "").strip()
    if not login or not password:
        return None
    return login, password


def send_sms_code(phone: str, code: str) -> None:
    """
    Send verification SMS via SMSC.ru HTTP API.
    If SMSC_LOGIN / SMSC_PASSWORD are not set, prints code to console (dev mode).

    SMSC.ru endpoint: GET https://smsc.ru/sys/send.php
    Parameters:
      login, psw  — credentials
      phones      — recipient phone (international format, e.g. +79991234567)
      mes         — message text
      charset     — utf-8 (required for Russian text)
      fmt         — 3 (JSON response)
      sender      — alphanumeric name shown to recipient (optional, must be pre-registered)
    """
    print(f"[INFO] Sending SMS to {phone}")
    creds = _smsc_credentials()
    if creds is None:
        return

    login, password = creds
    message = f"WayToOffer: ваш код подтверждения {code}. Никому не сообщайте."

    params: dict = {
        "login": login,
        "psw": password,
        "phones": phone,
        "mes": message,
        "charset": "utf-8",
        "fmt": 3,  # JSON response
    }

    # Убрали передачу sender="WayToOffer", чтобы SMSC.ru использовал дефолтное имя
    # и не отклонял сообщения с ошибкой 6 (message is denied)
    # sender = os.getenv("SMSC_SENDER", "").strip()
    # if sender:
    #     params["sender"] = sender

    try:
        resp = requests.get(SMSC_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "error_code" in data:
            print(f"[ERROR] SMSC.ru SMS error {data['error_code']}: {data.get('error')}")
    except Exception as exc:
        print(f"[ERROR] Failed to send SMS to {phone}: {exc}")


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_code(email: str, code: str) -> None:
    """
    Отправка email через SMTP (Google/Yandex/др.).
    """
    print(f"[INFO] Sending email to {email}")

    smtp_server = os.getenv("SMTP_SERVER", "").strip()
    smtp_port = os.getenv("SMTP_PORT", "465").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()

    if not smtp_server or not smtp_user or not smtp_pass:
        print("[ERROR] SMTP credentials not configured. Check SMTP_SERVER, SMTP_USER, SMTP_PASSWORD in .env")
        return

    subject = "Ваш код подтверждения — WayToOffer"
    body = (
        f"Привет!\n\n"
        f"Ваш код подтверждения для WayToOffer:\n\n"
        f"    {code}\n\n"
        f"Код действителен 10 минут.\n"
        f"Если вы не запрашивали код — проигнорируйте это письмо."
    )

    msg = MIMEMultipart()
    msg["From"] = f"WayToOffer <{smtp_user}>"
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        # Яндекс Почта: SSL, порт 465
        server = smtplib.SMTP_SSL(smtp_server, int(smtp_port), timeout=10)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, email, msg.as_string())
        server.quit()
    except Exception as exc:
        print(f"[ERROR] Failed to send email via SMTP to {email}: {exc}")
