import pytest
from pydantic import ValidationError

from app.config import Settings


def make_settings(**overrides: str) -> Settings:
    values = {
        "api_key": "test-api-key-long-enough",
        "smtp_host": "smtp.example.com",
        "smtp_user": "hello@example.com",
        "smtp_password": "secret-password",
        "smtp_from": "hello@example.com",
        "smtp_reply_to": "hello@example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_secrets_are_not_exposed_in_settings_repr() -> None:
    representation = repr(make_settings())
    assert "secret-password" not in representation
    assert "test-api-key-long-enough" not in representation


def test_public_urls_must_use_https() -> None:
    with pytest.raises(ValidationError):
        make_settings(support_url="http://example.com/support")


def test_from_name_rejects_header_injection() -> None:
    with pytest.raises(ValidationError):
        make_settings(smtp_from_name="FITNATION\nBcc: victim@example.com")
