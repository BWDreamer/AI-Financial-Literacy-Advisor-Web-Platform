from sqlalchemy import JSON, Column, DateTime, Integer, func

from app.core.database import Base


class AdvisorySettings(Base):
    __tablename__ = "advisory_settings"

    id = Column(Integer, primary_key=True)
    topics = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
