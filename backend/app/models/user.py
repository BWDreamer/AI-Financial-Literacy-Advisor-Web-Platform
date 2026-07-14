from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    username = Column(
        String(50),
        nullable=True,
    )

    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)

    avatar_url = Column(
        Text,
        nullable=True,
    )

    password_hash = Column(
        Text,
        nullable=False,
    )

    role = Column(
        String(50),
        nullable=False,
        default="user",
    )

    onboarding_completed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    @property
    def user_id(self) -> str:
        return f"USR-{self.id:04d}"

    @property
    def is_online(self) -> bool:
        if self.last_seen_at is None:
            return False

        last_seen = self.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        return last_seen >= datetime.now(timezone.utc) - timedelta(minutes=5)
