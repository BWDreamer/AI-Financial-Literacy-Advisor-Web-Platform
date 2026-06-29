from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    region = Column(
        String(100),
        nullable=False,
    )

    monthly_income = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    fixed_expenses = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    current_savings = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    initial_savings_target = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )