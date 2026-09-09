import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.services.email_service import EmailAuthenticationError, EmailService


def settings() -> Settings:
    return Settings(
        api_key="test-api-key-long-enough",
        smtp_host="smtp.example.test",
        smtp_user="hello@example.com",
        smtp_password="secret",
        smtp_from="hello@example.com",
        smtp_reply_to="hello@example.com",
    )


@patch("app.services.email_service.smtplib.SMTP_SSL")
def test_email_service_sends_multipart_message(smtp_ssl: MagicMock) -> None:
    smtp = smtp_ssl.return_value
    EmailService(settings()).send(
        recipient="client@example.com",
        subject="Test",
        html_body="<strong>Hello</strong>",
        text_body="Hello",
    )
    smtp.login.assert_called_once_with("hello@example.com", "secret")
    smtp.send_message.assert_called_once()
    message = smtp.send_message.call_args.args[0]
    assert message.is_multipart()
    assert message["Reply-To"] == "hello@example.com"
    smtp.quit.assert_called_once()


@patch("app.services.email_service.smtplib.SMTP_SSL")
def test_authentication_error_is_sanitized(smtp_ssl: MagicMock) -> None:
    smtp = smtp_ssl.return_value
    smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    with pytest.raises(EmailAuthenticationError, match="authentication failed"):
        EmailService(settings()).send(
            recipient="client@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
            text_body="Hello",
        )


@patch("app.services.email_service.smtplib.SMTP_SSL")
def test_quit_failure_does_not_turn_successful_delivery_into_failure(smtp_ssl: MagicMock) -> None:
    smtp = smtp_ssl.return_value
    smtp.quit.side_effect = smtplib.SMTPServerDisconnected("already closed")
    EmailService(settings()).send(
        recipient="client@example.com",
        subject="Test",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )
    smtp.send_message.assert_called_once()
    smtp.close.assert_called_once()
