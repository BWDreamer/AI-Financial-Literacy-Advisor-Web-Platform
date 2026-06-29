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
) -> User:
    user.email = new_email.lower().strip()

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


def touch_last_seen(db: Session, user: User) -> User:
    user.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
