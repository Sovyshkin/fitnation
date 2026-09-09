from pathlib import Path

import pytest

from app.services.template_service import TemplateService, TemplateServiceError


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "app" / "templates" / "emails"


def test_welcome_template_renders_and_escapes() -> None:
    html = TemplateService(TEMPLATE_DIR).render(
        "welcome_day1.html",
        {
            "recipient_name": "<Анна>",
            "club_name": "FITNATION",
            "support_url": "https://example.com/support",
            "logo_url": "https://example.com/logo.png",
        },
    )
    assert "&lt;Анна&gt;" in html
    assert "500 баллов" in html


def test_template_traversal_is_rejected() -> None:
    with pytest.raises(TemplateServiceError, match="Invalid template name"):
        TemplateService(TEMPLATE_DIR).render("../secret.html", {})


def test_all_email_templates_render() -> None:
    context = {
        "recipient_name": "Анна",
        "club_name": "FITNATION",
        "support_url": "https://example.com/support",
        "logo_url": "https://example.com/logo.png",
        "tariff_name": "Premium",
        "payment_amount": "3900",
        "next_payment_date": "15.09.2026",
        "membership_end_date": "30.09.2026",
    }
    service = TemplateService(TEMPLATE_DIR)
    for template_path in TEMPLATE_DIR.glob("*.html"):
        assert "FITNATION" in service.render(template_path.name, context)
