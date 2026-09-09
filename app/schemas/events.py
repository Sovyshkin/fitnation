from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


class EventType(StrEnum):
    WELCOME_DAY1 = "WELCOME_DAY1"
    BONUS_DAY15 = "BONUS_DAY15"
    SUBSCRIPTION_4DAYS_BEFORE = "SUBSCRIPTION_4DAYS_BEFORE"
    MEMBERSHIP_4DAYS_BEFORE = "MEMBERSHIP_4DAYS_BEFORE"
    SUBSCRIPTION_1DAY_BEFORE = "SUBSCRIPTION_1DAY_BEFORE"
    SUBSCRIPTION_OVERDUE_DAY1 = "SUBSCRIPTION_OVERDUE_DAY1"
    MEMBERSHIP_EXPIRED_DAY1 = "MEMBERSHIP_EXPIRED_DAY1"
    SUBSCRIPTION_OVERDUE_NEXT_DAY = "SUBSCRIPTION_OVERDUE_NEXT_DAY"
    SUBSCRIPTION_OVERDUE_DAY5 = "SUBSCRIPTION_OVERDUE_DAY5"
    MEMBERSHIP_EXPIRED_DAY5 = "MEMBERSHIP_EXPIRED_DAY5"
    SUBSCRIPTION_OVERDUE_DAY10 = "SUBSCRIPTION_OVERDUE_DAY10"
    MEMBERSHIP_EXPIRED_DAY10 = "MEMBERSHIP_EXPIRED_DAY10"


class Recipient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        if any(ord(character) < 32 for character in value):
            raise ValueError("name must not contain control characters")
        return value


class EventData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    support_url: HttpUrl | None = None
    club_name: str | None = Field(default=None, max_length=100)
    tariff_name: str | None = Field(default=None, max_length=100)
    payment_amount: str | None = Field(default=None, max_length=50)
    next_payment_date: str | None = Field(default=None, max_length=50)
    membership_end_date: str | None = Field(default=None, max_length=50)

    @field_validator("support_url")
    @classmethod
    def require_https(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None:
            if value.scheme != "https":
                raise ValueError("URL must use HTTPS")
            if len(str(value)) > 500:
                raise ValueError("URL must not exceed 500 characters")
        return value


class EventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: EventType
    recipient: Recipient
    data: EventData = Field(default_factory=EventData)


class TestEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: EmailStr
