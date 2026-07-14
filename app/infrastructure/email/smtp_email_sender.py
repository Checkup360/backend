import logging
import smtplib
from email.message import EmailMessage

from app.application.interfaces import EmailSender
from app.infrastructure.config import settings
from app.infrastructure.email.templates import (
    get_invite_email_html,
    get_invite_email_text,
    get_password_reset_email_html,
    get_password_reset_email_text,
)

logger = logging.getLogger(__name__)


class SmtpEmailSender(EmailSender):
    SMTP_TIMEOUT_SECONDS = 10

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password

    def send_invite_email(
        self,
        to_email: str,
        invite_url: str,
        is_sysadmin: bool = False,
        role: str = "",
        organization_name: str = "",
        department_name: str = "",
    ) -> None:
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials are not configured; email was not sent")
            return

        html_content = get_invite_email_html(
            action_url=invite_url,
            name=to_email,
            is_sysadmin=is_sysadmin,
            role=role,
            organization_name=organization_name,
            department_name=department_name,
        )
        text_content = get_invite_email_text(
            action_url=invite_url,
            name=to_email,
            is_sysadmin=is_sysadmin,
            role=role,
            organization_name=organization_name,
            department_name=department_name,
        )

        msg = EmailMessage()
        msg["Subject"] = "You have been invited to join CheckUp360"
        msg["From"] = self.smtp_user
        msg["To"] = to_email

        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype="html")

        self._send_message(msg)

    def send_password_reset_email(self, to_email: str, reset_url: str) -> None:
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials are not configured; email was not sent")
            return

        message = EmailMessage()
        message["Subject"] = "Reset your CheckUp360 password"
        message["From"] = self.smtp_user
        message["To"] = to_email
        message.set_content(get_password_reset_email_text(reset_url))
        message.add_alternative(
            get_password_reset_email_html(reset_url), subtype="html"
        )
        self._send_message(message)

    def _send_message(self, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(
                self.smtp_host,
                self.smtp_port,
                timeout=self.SMTP_TIMEOUT_SECONDS,
            ) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(message)
            logger.info("Email sent via SMTP")
        except Exception:
            logger.error("SMTP email delivery failed")
