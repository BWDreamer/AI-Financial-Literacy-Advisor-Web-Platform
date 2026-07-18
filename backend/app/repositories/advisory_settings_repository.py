from sqlalchemy.orm import Session

from app.models.advisory_settings import AdvisorySettings


GLOBAL_ADVISORY_SETTINGS_ID = 1


def find_advisory_settings(db: Session) -> AdvisorySettings | None:
    return db.get(AdvisorySettings, GLOBAL_ADVISORY_SETTINGS_ID)


def save_advisory_settings(
    db: Session,
    topics: list[dict[str, object]],
) -> AdvisorySettings:
    settings = find_advisory_settings(db)
    if settings is None:
        settings = AdvisorySettings(
            id=GLOBAL_ADVISORY_SETTINGS_ID,
            topics=topics,
        )
    else:
        settings.topics = topics

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
