from typing import Protocol


class EmailSender(Protocol):
    def send_invite_email(
        self,
        to_email: str,
        invite_url: str,
        is_sysadmin: bool = False,
        role: str = "",
        organization_name: str = "",
        department_name: str = "",
    ) -> None: ...

    def send_password_reset_email(self, to_email: str, reset_url: str) -> None: ...
