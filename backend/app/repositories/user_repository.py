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
        role="user",
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