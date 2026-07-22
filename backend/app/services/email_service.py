import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


def send_verification_email(
    *,
    recipient: str,
    code: str,
    purpose: str,
    expires_in_seconds: int,
) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise EmailDeliveryError(
            "Email delivery is not configured."
        )

    action = (
        "complete your registration"
        if purpose == "registration"
        else "confirm your new email address"
    )
    minutes = max(1, expires_in_seconds // 60)
    message = EmailMessage()
    message["Subject"] = f"{settings.app_name} email verification code"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                f"Use this verification code to {action}:",
                "",
                code,
                "",
                f"This code expires in {minutes} minutes.",
                "If you did not request this code, you can ignore this email.",
            ]
        )
    )

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as smtp:
            if settings.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                smtp.login(
                    settings.smtp_username,
                    settings.smtp_password.get_secret_value(),
                )
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError(
            "The verification email could not be sent."
        ) from error
