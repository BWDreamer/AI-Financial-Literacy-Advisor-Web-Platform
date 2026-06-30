import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.admin_service import create_admin_user


def main() -> int:
    if not settings.admin_email or not settings.admin_password:
        print("ADMIN_EMAIL and ADMIN_PASSWORD must be configured in .env.")
        return 1

    db = SessionLocal()
    try:
        user, result = create_admin_user(
            db=db,
            email=settings.admin_email,
            password=settings.admin_password,
            name=settings.admin_name,
        )
    except ValueError as error:
        print(str(error))
        return 1
    except Exception:
        db.rollback()
        print("Unable to create the administrator account. Check the database connection.")
        return 1
    finally:
        db.close()

    messages = {
        "created": "Administrator account created.",
        "upgraded": "Existing user upgraded to administrator.",
        "already_exists": "Administrator account already exists; no changes were made.",
    }
    print(f"{messages[result]} Email: {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
