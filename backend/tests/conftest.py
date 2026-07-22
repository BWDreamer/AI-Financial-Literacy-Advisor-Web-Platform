import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.services import email_service

# These imports register the database tables with SQLAlchemy.
from app.models.advisory_settings import AdvisorySettings
from app.models.financial_rule import FinancialRule
from app.models.financial import Asset, CashBucket, CashFlow, Debt, RecurringCashFlow
from app.models.chat import ChatConversation, ChatMessage
from app.models.email_verification import EmailVerificationCode
from app.models.article import Article, ArticleLike, ArticleSave
from app.models.goal import (
    Goal,
    GoalAllocationSettings,
    GoalPlanConfirmation,
    GoalProgress,
)
from app.models.user import User
from app.models.user_profile import UserProfile


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sent_verification_codes(monkeypatch):
    codes: dict[str, str] = {}

    def capture_verification_code(
        *,
        recipient: str,
        code: str,
        purpose: str,
        expires_in_seconds: int,
    ):
        codes[recipient] = code

    monkeypatch.setattr(
        email_service,
        "send_verification_email",
        capture_verification_code,
    )
    return codes


@pytest.fixture
def client(sent_verification_codes):
    with TestClient(app) as test_client:
        test_client.sent_verification_codes = sent_verification_codes
        yield test_client


@pytest.fixture
def db_session():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
