from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func

from app.core.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    target_amount = Column(Numeric(14, 2), nullable=False)
    current_amount = Column(Numeric(14, 2), nullable=False, default=0)
    monthly_contribution = Column(Numeric(14, 2), nullable=False, default=0)
    target_date = Column(Date, nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="on_track")
    category_details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class GoalProgress(Base):
    __tablename__ = "goal_progress"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    progress_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, default="manual")
    new_current_amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class GoalAllocationSettings(Base):
    __tablename__ = "goal_allocation_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    cash_allocatable_ratio = Column(Numeric(5, 2), nullable=False, default=50)
    monthly_allocatable_ratio = Column(Numeric(5, 2), nullable=False, default=50)
    goal_monthly_ratios = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
