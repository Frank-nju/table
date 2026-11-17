"""Email service.
Encapsulates email delivery and related business logic."""

import logging
import smtplib
import threading
from email.message import EmailMessage

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_SSL,
    SENDER_EMAIL, SENDER_NAME
)

logger = logging.getLogger(__name__)


class EmailService:
    """Email delivery service."""

    @staticmethod
    def is_configured():
        """Check whether email is configured."""
        return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)

    @staticmethod
    def send(recipient, subject, body):
        """Send an email."""
        if not EmailService.is_configured():
            logger.warning("Email not configured, skip sending")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = recipient
        msg.set_content(body)

        try:
            if SMTP_USE_SSL:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                    smtp.starttls()
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                    smtp.send_message(msg)
            return True
        except Exception as e:
            logger.error("Send email failed: %s", e)
            return False

    @staticmethod
    def send_async(recipient, subject, body):
        """Send an email asynchronously."""
        thread = threading.Thread(
            target=EmailService.send,
            args=(recipient, subject, body),
            daemon=True
        )
        thread.start()


# Convenience helpers
def send_email(recipient, subject, body):
    """Send an email."""
    return EmailService.send(recipient, subject, body)


def send_email_async(recipient, subject, body):
    """Send an email asynchronously."""
    EmailService.send_async(recipient, subject, body)