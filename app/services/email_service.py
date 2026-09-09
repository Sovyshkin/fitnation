import smtplib
import socket
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.config import Settings


class EmailDeliveryError(RuntimeError):
    code = "smtp_error"


class EmailAuthenticationError(EmailDeliveryError):
    code = "smtp_auth_failed"


class EmailConnectionError(EmailDeliveryError):
    code = "smtp_connection_failed"


class EmailRecipientError(EmailDeliveryError):
    code = "smtp_recipient_refused"


class EmailService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, *, recipient: str, subject: str, html_body: str, text_body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self._settings.smtp_from_name, str(self._settings.smtp_from)))
        message["To"] = recipient
        message["Reply-To"] = str(self._settings.smtp_reply_to)
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        smtp: smtplib.SMTP_SSL | None = None
        try:
            context = ssl.create_default_context()
            smtp = smtplib.SMTP_SSL(
                self._settings.smtp_host,
                self._settings.smtp_port,
                timeout=self._settings.smtp_timeout,
                context=context,
            )
            smtp.login(
                str(self._settings.smtp_user),
                self._settings.smtp_password.get_secret_value(),
            )
            smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailAuthenticationError("SMTP authentication failed") from exc
        except smtplib.SMTPRecipientsRefused as exc:
            raise EmailRecipientError("Recipient was refused") from exc
        except (socket.timeout, TimeoutError, ConnectionError, OSError, smtplib.SMTPServerDisconnected) as exc:
            raise EmailConnectionError("SMTP connection failed") from exc
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError("SMTP delivery failed") from exc
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except (OSError, smtplib.SMTPException):
                    smtp.close()
