from pathlib import Path
from html import escape

TEMPLATES_DIR = Path(__file__).parent / "templates"


def get_invite_email_html(
    action_url: str,
    name: str,
    is_sysadmin: bool = False,
    role: str = "",
    organization_name: str = "",
    department_name: str = "",
) -> str:
    if is_sysadmin:
        message = "You have been invited to join CheckUp360 as a system administrator."
    else:
        dept_str = (
            f" and in the {department_name} department" if department_name else ""
        )
        message = f"You have been invited to join the organization {organization_name}, with the role of {role}{dept_str}."

    html_path = TEMPLATES_DIR / "invite.html"
    content = html_path.read_text(encoding="utf-8")

    return (
        content.replace("{name}", name)
        .replace("{message}", message)
        .replace("{action_url}", action_url)
    )


def get_invite_email_text(
    action_url: str,
    name: str,
    is_sysadmin: bool = False,
    role: str = "",
    organization_name: str = "",
    department_name: str = "",
) -> str:
    if is_sysadmin:
        message = "You have been invited to join CheckUp360 as a system administrator."
    else:
        dept_str = (
            f" and in the {department_name} department" if department_name else ""
        )
        message = f"You have been invited to join the organization {organization_name}, with the role of {role}{dept_str}."

    txt_path = TEMPLATES_DIR / "invite.txt"
    content = txt_path.read_text(encoding="utf-8")

    return (
        content.replace("{name}", name)
        .replace("{message}", message)
        .replace("{action_url}", action_url)
    )


def get_password_reset_email_html(action_url: str) -> str:
    content = (TEMPLATES_DIR / "password_reset.html").read_text(encoding="utf-8")
    return content.replace("{action_url}", escape(action_url, quote=True))


def get_password_reset_email_text(action_url: str) -> str:
    content = (TEMPLATES_DIR / "password_reset.txt").read_text(encoding="utf-8")
    return content.replace("{action_url}", action_url)
