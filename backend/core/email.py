from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import settings


def _smtp_timeout_seconds() -> int:
    try:
        return max(1, int(getattr(settings, "SMTP_TIMEOUT_SECONDS", 10)))
    except (TypeError, ValueError):
        return 10


def send_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    timeout = _smtp_timeout_seconds()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout) as smtp:
        smtp.ehlo()
        if bool(getattr(settings, "SMTP_USE_TLS", False)):
            smtp.starttls()
            smtp.ehlo()
        if settings.SMTP_USER and settings.SMTP_PASS:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
        smtp.send_message(msg)


def send_password_reset_email(*, to_email: str, reset_link: str, expires_minutes: int = 60) -> None:
    subject = "Reset your Sponsorship Hub password"
    text_body = (
        "You requested a password reset for your Sponsorship Hub account.\n\n"
        f"Reset link (valid for about {expires_minutes} minutes):\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html_body = (
        "<p>You requested a password reset for your Sponsorship Hub account.</p>"
        f"<p><a href=\"{reset_link}\">Reset your password</a> "
        f"(valid for about {expires_minutes} minutes).</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
    )
    send_email(to_email=to_email, subject=subject, text_body=text_body, html_body=html_body)


def send_verification_email(*, to_email: str, verify_link: str, expires_hours: int = 24) -> None:
    subject = "Verify your Sponsorship Hub account"
    text_body = (
        "Welcome to Sponsorship Hub.\n\n"
        "Please verify your email to activate your account.\n"
        f"Verification link (valid for about {expires_hours} hours):\n"
        f"{verify_link}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    html_body = (
        "<p>Welcome to Sponsorship Hub.</p>"
        "<p>Please verify your email to activate your account.</p>"
        f"<p><a href=\"{verify_link}\">Verify Email</a> "
        f"(valid for about {expires_hours} hours).</p>"
        "<p>If you did not create this account, you can ignore this email.</p>"
    )
    send_email(to_email=to_email, subject=subject, text_body=text_body, html_body=html_body)
