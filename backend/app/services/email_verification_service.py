import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_verification import EmailVerificationCode
from app.repositories.email_verification_repository import (
    create_verification_code,
    find_latest_verification_code,
    invalidate_verification_codes,
)
from app.services import email_service


VerificationPurpose = Literal["registration", "email_change", "password_reset"]


class VerificationCodeError(ValueError):
    pass


class VerificationCodeCooldownError(VerificationCodeError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Please wait before requesting another code.")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _code_hash(
    *,
    email: str,
    purpose: VerificationPurpose,
    user_id: int | None,
    code: str,
) -> str:
    payload = (
        f"{settings.jwt_secret_key}:{email}:{purpose}:"
        f"{user_id or ''}:{code}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def request_verification_code(
    db: Session,
    *,
    email: str,
    purpose: VerificationPurpose,
    user_id: int | None = None,
) -> int:
    normalized_email = email.lower().strip()
    now = datetime.now(timezone.utc)
    latest = find_latest_verification_code(
        db,
        email=normalized_email,
        purpose=purpose,
        user_id=user_id,
    )
    if latest is not None:
        elapsed = (now - _as_utc(latest.created_at)).total_seconds()
        remaining = settings.email_verification_resend_seconds - elapsed
        if remaining > 0:
            raise VerificationCodeCooldownError(max(1, int(remaining) + 1))

    code = f"{secrets.randbelow(1_000_000):06d}"
    email_service.send_verification_email(
        recipient=normalized_email,
        code=code,
        purpose=purpose,
        expires_in_seconds=settings.email_verification_ttl_seconds,
    )
    invalidate_verification_codes(
        db,
        email=normalized_email,
        purpose=purpose,
        user_id=user_id,
        consumed_at=now,
    )
    create_verification_code(
        db,
        email=normalized_email,
        purpose=purpose,
        user_id=user_id,
        code_hash=_code_hash(
            email=normalized_email,
            purpose=purpose,
            user_id=user_id,
            code=code,
        ),
        expires_at=now
        + timedelta(seconds=settings.email_verification_ttl_seconds),
    )
    return settings.email_verification_ttl_seconds


def consume_verification_code(
    db: Session,
    *,
    email: str,
    purpose: VerificationPurpose,
    code: str,
    user_id: int | None = None,
) -> EmailVerificationCode:
    normalized_email = email.lower().strip()
    now = datetime.now(timezone.utc)
    record = find_latest_verification_code(
        db,
        email=normalized_email,
        purpose=purpose,
        user_id=user_id,
    )
    if (
        record is None
        or record.consumed_at is not None
        or _as_utc(record.expires_at) <= now
        or record.attempts >= settings.email_verification_max_attempts
    ):
        raise VerificationCodeError(
            "The verification code is invalid or has expired."
        )

    expected_hash = _code_hash(
        email=normalized_email,
        purpose=purpose,
        user_id=user_id,
        code=code,
    )
    if not hmac.compare_digest(record.code_hash, expected_hash):
        record.attempts += 1
        if record.attempts >= settings.email_verification_max_attempts:
            record.consumed_at = now
        db.add(record)
        db.commit()
        raise VerificationCodeError(
            "The verification code is invalid or has expired."
        )

    record.consumed_at = now
    db.add(record)
    db.flush()
    return record
