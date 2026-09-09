#!/usr/bin/env python3
import smtplib
import socket
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402


def main() -> int:
    settings = get_settings()
    recipient = sys.argv[1] if len(sys.argv) > 1 else settings.smtp_from
    message = EmailMessage()
    message["Subject"] = "FITNATION: проверка SMTP"
    message["From"] = formataddr((settings.smtp_from_name, str(settings.smtp_from)))
    message["To"] = recipient
    message["Reply-To"] = str(settings.smtp_reply_to)
    message.set_content("SMTP FITNATION настроен и работает.")

    try:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout,
            context=ssl.create_default_context(),
        ) as smtp:
            smtp.login(str(settings.smtp_user), settings.smtp_password.get_secret_value())
            print("SMTP LOGIN OK")
            smtp.send_message(message)
            print("EMAIL SENT")
    except smtplib.SMTPAuthenticationError:
        print("ERROR: SMTP authentication failed. Check the Yandex app password.", file=sys.stderr)
        return 2
    except (socket.timeout, TimeoutError, ConnectionError, OSError, smtplib.SMTPServerDisconnected):
        print("ERROR: Could not connect to the SMTP server.", file=sys.stderr)
        return 3
    except smtplib.SMTPException:
        print("ERROR: SMTP rejected the message.", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
