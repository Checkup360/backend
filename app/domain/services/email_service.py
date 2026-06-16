import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.email_templates import get_invite_email_html, get_invite_email_text

logger = logging.getLogger(__name__)


class EmailService:
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
            logger.warning(
                f"SMTP_USER or SMTP_PASSWORD is not set. Simulating email send to {to_email} with URL: {invite_url}"
            )
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

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            logger.info(f"Invitation sent to {to_email} via SMTP.")
        except Exception as e:
            logger.error(f"Error sending invitation email to {to_email}: {e}")
