import logging
import resend

from app.core.config import settings
from app.core.email_templates import get_invite_email_html, get_invite_email_text

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.api_key = settings.resend_api_key
        self.from_email = settings.resend_from_email
        if self.api_key:
            resend.api_key = self.api_key

    def send_invite_email(
        self,
        to_email: str,
        invite_url: str,
        is_sysadmin: bool = False,
        role: str = "",
        organization_name: str = "",
        department_name: str = "",
    ) -> None:
        if not self.api_key:
            logger.warning(
                f"RESEND_API_KEY is not set. Simulating email send to {to_email} with URL: {invite_url}"
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

        try:
            r = resend.Emails.send(
                {
                    "from": self.from_email,
                    "to": to_email,
                    "subject": "Has sido invitado a unirte a la plataforma",
                    "html": html_content,
                    "text": text_content,
                }
            )
            logger.info(f"Invitation sent to {to_email}. Resend response: {r}")
        except Exception as e:
            logger.error(f"Error sending invitation email to {to_email}: {e}")
