from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
)

from app.core.database import Base


class FinancialRule(Base):
    __tablename__ = "financial_rules"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    region = Column(
        String(100),
        nullable=False,
        index=True,
    )

    category = Column(
        String(100),
        nullable=False,
        index=True,
    )

    rule_year = Column(
        String(20),
        nullable=False,
        index=True,
    )

    rule_key = Column(
        String(100),
        nullable=False,
    )

    rule_value = Column(
        Text,
        nullable=False,
    )

    source_name = Column(
        String(255),
        nullable=True,
    )

    source_url = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )