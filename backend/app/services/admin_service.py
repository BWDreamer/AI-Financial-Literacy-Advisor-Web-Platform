from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import create_user, get_user_by_email


def create_admin_user(
    db: Session,
    email: str,
    password: str,
    name: str | None = None,
) -> tuple[User, str]:
    normalized_email = email.lower().strip()
    normalized_name = name.strip() if name and name.strip() else "Admin"

    if "@" not in normalized_email:
        raise ValueError("ADMIN_EMAIL must be a valid email address.")
    if len(password) < 8 or len(password) > 72:
        raise ValueError("ADMIN_PASSWORD must contain 8 to 72 characters.")

    existing_user = get_user_by_email(db, normalized_email)
    if existing_user is not None:
        if existing_user.role == "admin":
            return existing_user, "already_exists"

        existing_user.role = "admin"
        existing_user.username = normalized_name
        existing_user.password_hash = hash_password(password)
        db.commit()
        db.refresh(existing_user)
        return existing_user, "upgraded"

    user = create_user(
        db=db,
        email=normalized_email,
        username=normalized_name,
        password_hash=hash_password(password),
        role="admin",
    )
    return user, "created"
