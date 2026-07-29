from app.infrastructure.email.templates import (
    get_invite_email_html,
    get_invite_email_text,
    get_password_reset_email_html,
    get_password_reset_email_text,
)


def test_get_invite_email_html_sysadmin():
    html = get_invite_email_html(
        action_url="https://app.example.com/invite/tok123",
        name="Admin User",
        is_sysadmin=True,
    )
    assert "Admin User" in html
    assert "system administrator" in html
    assert "https://app.example.com/invite/tok123" in html


def test_get_invite_email_html_organization_and_department():
    html = get_invite_email_html(
        action_url="https://app.example.com/invite/tok456",
        name="Member User",
        is_sysadmin=False,
        role="member",
        organization_name="Acme Health",
        department_name="Engineering",
    )
    assert "Member User" in html
    assert "Acme Health" in html
    assert "role of member" in html
    assert "Engineering" in html
    assert "https://app.example.com/invite/tok456" in html


def test_get_invite_email_text_sysadmin():
    text = get_invite_email_text(
        action_url="https://app.example.com/invite/tok123",
        name="Admin User",
        is_sysadmin=True,
    )
    assert "Admin User" in text
    assert "system administrator" in text
    assert "https://app.example.com/invite/tok123" in text


def test_get_invite_email_text_organization_and_department():
    text = get_invite_email_text(
        action_url="https://app.example.com/invite/tok456",
        name="Member User",
        is_sysadmin=False,
        role="member",
        organization_name="Acme Health",
        department_name="Engineering",
    )
    assert "Member User" in text
    assert "Acme Health" in text
    assert "role of member" in text
    assert "Engineering" in text
    assert "https://app.example.com/invite/tok456" in text


def test_get_password_reset_email_html():
    html = get_password_reset_email_html("https://app.example.com/reset?token=xyz")
    assert "https://app.example.com/reset?token=xyz" in html


def test_get_password_reset_email_text():
    text = get_password_reset_email_text("https://app.example.com/reset?token=xyz")
    assert "https://app.example.com/reset?token=xyz" in text
