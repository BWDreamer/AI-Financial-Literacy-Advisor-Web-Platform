from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .filter(User.email == email.lower().strip())
        .first()
    )


def create_user(
    db: Session,
    email: str,
    password_hash: str,
) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=password_hash,
        role="user",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user