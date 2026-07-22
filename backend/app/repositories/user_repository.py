from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_id(
    db: Session,
    user_id: int,
) -> User | None:
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    normalized_email = email.lower().strip()

    return (
        db.query(User)
        .filter(User.email == normalized_email)
        .first()
    )


def create_user(
    db: Session,
    email: str,
    password_hash: str,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    role: str = "user",
    email_verified_at: datetime | None = None,
) -> User:
    normalized_email = email.lower().strip()

    user = User(
        email=normalized_email,
        username=(
            username.strip()
            if username
            else normalized_email.split("@")[0]
        ),
        password_hash=password_hash,
        first_name=first_name.strip() if first_name else None,
        last_name=last_name.strip() if last_name else None,
        role=role,
        email_verified_at=email_verified_at,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def update_username(
    db: Session,
    user: User,
    username: str,
) -> User:
    user.username = username.strip()

    db.commit()
    db.refresh(user)

    return user


def update_email(
    db: Session,
    user: User,
    new_email: str,
    email_verified_at: datetime,
) -> User:
    user.email = new_email.lower().strip()
    user.email_verified_at = email_verified_at

    db.commit()
    db.refresh(user)

    return user


def update_password_hash(
    db: Session,
    user: User,
    password_hash: str,
) -> User:
    user.password_hash = password_hash

    db.commit()
    db.refresh(user)

    return user


def update_avatar_url(
    db: Session,
    user: User,
    avatar_url: str,
) -> User:
    user.avatar_url = avatar_url

    db.commit()
    db.refresh(user)

    return user


def update_onboarding_completed(
    db: Session,
    user: User,
    completed: bool,
) -> User:
    user.onboarding_completed = completed

    db.commit()
    db.refresh(user)

    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id).all()


def update_admin_user(
    db: Session,
    user: User,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
) -> User:
    if first_name is not None:
        user.first_name = first_name.strip()
    if last_name is not None:
        user.last_name = last_name.strip()
    if email is not None:
        user.email = email.lower().strip()
    user.username = f"{user.first_name} {user.last_name}"
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def delete_user_account(db: Session, user: User) -> None:
    from app.models.chat import ChatConversation, ChatMessage
    from app.models.email_verification import EmailVerificationCode
    from app.models.financial import Asset, CashFlow
    from app.models.user_profile import UserProfile

    conversation_ids = [
        row[0]
        for row in db.query(ChatConversation.id).filter(
            ChatConversation.user_id == user.id
        ).all()
    ]
    if conversation_ids:
        db.query(ChatMessage).filter(
            ChatMessage.conversation_id.in_(conversation_ids)
        ).delete(synchronize_session=False)
    db.query(ChatConversation).filter(
        ChatConversation.user_id == user.id
    ).delete(synchronize_session=False)
    db.query(Asset).filter(Asset.user_id == user.id).delete()
    db.query(CashFlow).filter(CashFlow.user_id == user.id).delete()
    db.query(UserProfile).filter(UserProfile.user_id == user.id).delete()
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.user_id == user.id
    ).delete()
    db.delete(user)
    db.commit()


def touch_last_seen(db: Session, user: User) -> User:
    user.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
