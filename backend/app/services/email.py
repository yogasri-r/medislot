import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger("medislot.email")

class SentEmailRecord:
    def __init__(self, recipient: str, subject: str, body_text: str, body_html: Optional[str] = None):
        self.recipient = recipient
        self.subject = subject
        self.body_text = body_text
        self.body_html = body_html
        self.sent_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipient": self.recipient,
            "subject": self.subject,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "sent_at": self.sent_at.isoformat()
        }

class EmailSender:
    """
    Email service supporting 'console', 'mock', and 'smtp' providers.
    In development and testing, 'console' and 'mock' log to stdout and retain
    an inspection ledger for deterministic test assertions.
    """
    def __init__(self):
        self._sent_emails: List[SentEmailRecord] = []

    def clear(self):
        """Clears the inspection ledger (useful between test runs)."""
        self._sent_emails.clear()

    @property
    def sent_emails(self) -> List[SentEmailRecord]:
        return list(self._sent_emails)

    def get_last_email(self) -> Optional[SentEmailRecord]:
        return self._sent_emails[-1] if self._sent_emails else None

    def get_emails_for_recipient(self, recipient: str) -> List[SentEmailRecord]:
        return [e for e in self._sent_emails if e.recipient.lower() == recipient.lower()]

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> bool:
        record = SentEmailRecord(
            recipient=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )
        self._sent_emails.append(record)

        provider = settings.EMAIL_PROVIDER.lower()

        if provider in ["console", "mock", "development"]:
            print("\n" + "=" * 65)
            print("               [MediSlot EMAIL NOTIFICATION]             ")
            print("=" * 65)
            print(f"TO      : {to_email}")
            print(f"FROM    : {settings.SMTP_FROM_EMAIL}")
            print(f"SUBJECT : {subject}")
            print(f"DATE    : {record.sent_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print("-" * 65)
            print(body_text.strip())
            print("=" * 65 + "\n")
            return True

        elif provider == "smtp":
            if not settings.SMTP_HOST:
                logger.warning("SMTP provider chosen but SMTP_HOST is not set; falling back to console.")
                print(f"[FALLBACK EMAIL] To: {to_email} | Subject: {subject}")
                return True

            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_FROM_EMAIL
                msg["To"] = to_email

                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)

                if body_html:
                    part2 = MIMEText(body_html, "html")
                    msg.attach(part2)

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    if settings.SMTP_PORT == 587:
                        server.starttls()
                    if settings.SMTP_USER and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
                return True

            except Exception as ex:
                logger.error(f"Failed to send email via SMTP to {to_email}: {ex}")
                return False

        else:
            logger.info(f"[Email Disabled] To: {to_email} | Subject: {subject}")
            return True

# Singleton email sender instance
email_sender = EmailSender()
