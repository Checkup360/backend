from unittest.mock import MagicMock, patch

from app.infrastructure.email.smtp_email_sender import SmtpEmailSender


def test_send_invite_email_missing_credentials_logs_warning():
    sender = SmtpEmailSender()
    sender.smtp_user = ""
    sender.smtp_password = ""

    with patch.object(sender, "_send_message") as mock_send:
        sender.send_invite_email("to@example.com", "https://invite.url")
        mock_send.assert_not_called()


def test_send_invite_email_success():
    sender = SmtpEmailSender()
    sender.smtp_user = "sender@example.com"
    sender.smtp_password = "password123"

    with patch.object(sender, "_send_message") as mock_send:
        sender.send_invite_email(
            to_email="to@example.com",
            invite_url="https://app.example.com/invite/123",
            is_sysadmin=True,
        )

        mock_send.assert_called_once()
        msg = mock_send.call_args.args[0]
        assert msg["Subject"] == "You have been invited to join CheckUp360"
        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "to@example.com"


def test_send_password_reset_email_missing_credentials_logs_warning():
    sender = SmtpEmailSender()
    sender.smtp_user = ""
    sender.smtp_password = ""

    with patch.object(sender, "_send_message") as mock_send:
        sender.send_password_reset_email("user@example.com", "https://reset.url")
        mock_send.assert_not_called()


def test_send_password_reset_email_success():
    sender = SmtpEmailSender()
    sender.smtp_user = "sender@example.com"
    sender.smtp_password = "password123"

    with patch.object(sender, "_send_message") as mock_send:
        sender.send_password_reset_email("user@example.com", "https://reset.url")

        mock_send.assert_called_once()
        msg = mock_send.call_args.args[0]
        assert msg["Subject"] == "Reset your CheckUp360 password"
        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "user@example.com"


@patch("smtplib.SMTP")
def test_send_message_smtp_connection(mock_smtp_cls):
    sender = SmtpEmailSender()
    sender.smtp_host = "smtp.test.com"
    sender.smtp_port = 587
    sender.smtp_user = "user@test.com"
    sender.smtp_password = "secret_password"

    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    msg = MagicMock()
    sender._send_message(msg)

    mock_smtp_cls.assert_called_once_with("smtp.test.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user@test.com", "secret_password")
    mock_server.send_message.assert_called_once_with(msg)


@patch("smtplib.SMTP")
def test_send_message_handles_smtp_exception(mock_smtp_cls):
    sender = SmtpEmailSender()
    sender.smtp_user = "user@test.com"
    sender.smtp_password = "secret_password"

    mock_smtp_cls.side_effect = Exception("Connection error")

    # Should log error and not crash
    sender._send_message(MagicMock())
