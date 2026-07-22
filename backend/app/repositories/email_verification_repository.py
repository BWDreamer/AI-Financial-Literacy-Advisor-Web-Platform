from datetime import datetime

from sqlalchemy.orm import Session

from app.models.email_verification import EmailVerificationCode


def find_latest_verification_code(
    db: Session,
    *,
    email: str,
    purpose: str,
    user_id: int | None,
) -> EmailVerificationCode | None:
    query = db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.purpose == purpose,
    )
    if user_id is None:
        query = query.filter(EmailVerificationCode.user_id.is_(None))
    else:
        query = query.filter(EmailVerificationCode.user_id == user_id)
    return query.order_by(
        EmailVerificationCode.created_at.desc(),
        EmailVerificationCode.id.desc(),
    ).first()


def invalidate_verification_codes(
    db: Session,
    *,
    email: str,
    purpose: str,
    user_id: int | None,
    consumed_at: datetime,
) -> None:
    query = db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.purpose == purpose,
        EmailVerificationCode.consumed_at.is_(None),
    )
    if user_id is None:
        query = query.filter(EmailVerificationCode.user_id.is_(None))
    else:
        query = query.filter(EmailVerificationCode.user_id == user_id)
    query.update(
        {EmailVerificationCode.consumed_at: consumed_at},
        synchronize_session=False,
    )


def create_verification_code(
    db: Session,
    *,
    email: str,
    purpose: str,
    user_id: int | None,
    code_hash: str,
    expires_at: datetime,
) -> EmailVerificationCode:
    record = EmailVerificationCode(
        email=email,
        purpose=purpose,
        user_id=user_id,
        code_hash=code_hash,
        expires_at=expires_at,
        attempts=0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
