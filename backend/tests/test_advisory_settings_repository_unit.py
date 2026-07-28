from app.repositories.advisory_settings_repository import (
    GLOBAL_ADVISORY_SETTINGS_ID,
    find_advisory_settings,
    save_advisory_settings,
)


def test_find_advisory_settings_returns_none_when_missing(db_session):
    assert find_advisory_settings(db_session) is None


def test_save_advisory_settings_creates_global_settings(db_session):
    topics = [
        {"key": "budgeting", "label": "Budgeting", "enabled": True},
        {"key": "investing", "label": "Investing", "enabled": False},
    ]

    settings = save_advisory_settings(db_session, topics)

    assert settings.id == GLOBAL_ADVISORY_SETTINGS_ID
    assert settings.topics == topics
    assert find_advisory_settings(db_session).topics == topics


def test_save_advisory_settings_updates_existing_global_settings(db_session):
    save_advisory_settings(
        db_session,
        [{"key": "budgeting", "label": "Budgeting", "enabled": True}],
    )

    updated_topics = [
        {"key": "saving", "label": "Saving", "enabled": True},
        {"key": "tax", "label": "Tax", "enabled": False},
    ]
    settings = save_advisory_settings(db_session, updated_topics)

    assert settings.id == GLOBAL_ADVISORY_SETTINGS_ID
    assert settings.topics == updated_topics
    assert find_advisory_settings(db_session).topics == updated_topics
