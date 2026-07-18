from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.advisory_settings import AdvisorySettings
from app.models.user import User
from app.repositories.advisory_settings_repository import (
    find_advisory_settings,
    save_advisory_settings,
)
from app.repositories.user_repository import create_user, get_user_by_email
from app.schemas.admin import AdvisorySettingsUpdateRequest


DEFAULT_ADVISORY_TOPICS = {
    "Budgeting": True,
    "Saving": True,
    "Tax": True,
    "Superannuation": True,
    "Investing": False,
    "Debt": True,
}


def advisory_settings_payload(
    settings: AdvisorySettings | None,
) -> dict[str, list[dict[str, object]]]:
    values = DEFAULT_ADVISORY_TOPICS.copy()
    if settings is not None and isinstance(settings.topics, list):
        for topic in settings.topics:
            if not isinstance(topic, dict):
                continue
            name = topic.get("name")
            enabled = topic.get("enabled")
            if name in values and isinstance(enabled, bool):
                values[name] = enabled

    return {
        "topics": [
            {"name": name, "enabled": enabled}
            for name, enabled in values.items()
        ]
    }


def get_advisory_settings(db: Session) -> dict[str, list[dict[str, object]]]:
    return advisory_settings_payload(find_advisory_settings(db))


def update_advisory_settings(
    db: Session,
    request: AdvisorySettingsUpdateRequest,
) -> dict[str, list[dict[str, object]]]:
    current = get_advisory_settings(db)
    values = {
        topic["name"]: topic["enabled"]
        for topic in current["topics"]
    }
    values.update(
        {
            topic.name: topic.enabled
            for topic in request.topics
        }
    )
    topics = [
        {"name": name, "enabled": values[name]}
        for name in DEFAULT_ADVISORY_TOPICS
    ]
    return advisory_settings_payload(save_advisory_settings(db, topics))


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
