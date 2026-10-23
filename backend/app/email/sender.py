

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from typing import Protocol

from app.core.config import settings
from app.email.templates import RenderedEmail

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


@dataclass(slots=True)
class EmailMessagePayload:
    to_email: str
    subject: str
    html: str
    text: str
    from_email: str | None = None
    from_name: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


class EmailSender(Protocol):
    name: str

    def send(self, payload: EmailMessagePayload) -> None:
        ...


class SmtpEmailSender:
    

    name = "smtp"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        sender_name: str | None = None,
        use_starttls: bool | None = None,
        use_ssl: bool | None = None,
        timeout: int | None = None,
    ) -> None:
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.sender = sender if sender is not None else settings.SMTP_FROM
        self.sender_name = sender_name if sender_name is not None else settings.SMTP_FROM_NAME
        self.use_starttls = use_starttls if use_starttls is not None else settings.SMTP_STARTTLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.SMTP_USE_SSL
        self.timeout = timeout if timeout is not None else settings.SMTP_TIMEOUT_SECONDS

    def _build_message(self, payload: EmailMessagePayload) -> EmailMessage:
        message = EmailMessage()
        from_email = payload.from_email or self.sender
        from_name = payload.from_name or self.sender_name
        message["Subject"] = payload.subject
        message["From"] = formataddr((from_name, from_email))
        message["To"] = payload.to_email
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = f"<{id(payload):x}.{abs(hash(payload.subject)) & 0xFFFFFFFF:x}@library>"
        for key, value in payload.headers.items():
            message[key] = value
        message.set_content(payload.text or "")
        message.add_alternative(payload.html or payload.text or "", subtype="html")
        return message

    def send(self, payload: EmailMessagePayload) -> None:
        message = self._build_message(payload)
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout, context=context
                ) as server:
                    self._authenticate(server)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                    server.ehlo()
                    if self.use_starttls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                        server.ehlo()
                    self._authenticate(server)
                    server.send_message(message)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError(f"SMTP error: {exc.__class__.__name__}: {exc}") from exc
        except OSError as exc:
            raise EmailDeliveryError(f"SMTP connection error: {exc}") from exc

    def _authenticate(self, server: smtplib.SMTP) -> None:
        if self.username:
            try:
                server.login(self.username, self.password or "")
            except smtplib.SMTPException as exc:
                raise EmailDeliveryError(f"SMTP authentication failed: {exc}") from exc


class MockEmailSender:
    

    name = "mock"

    def __init__(self) -> None:
        self.sent: list[EmailMessagePayload] = []
        self.fail_times: int = 0
        self.raise_error: Exception | None = None

    def send(self, payload: EmailMessagePayload) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise EmailDeliveryError("Simulated SMTP failure")
        if self.raise_error is not None:
            raise self.raise_error
        self.sent.append(payload)


class ConsoleEmailSender:
    

    name = "console"

    def __init__(self) -> None:
        self.sent: list[EmailMessagePayload] = []

    def send(self, payload: EmailMessagePayload) -> None:
        self.sent.append(payload)
        logger.info(
            "EMAIL[console] to=%s subject=%s chars=%s",
            payload.to_email,
            payload.subject,
            len(payload.html or ""),
        )


_sender: EmailSender | None = None


def get_sender() -> EmailSender:
    
    global _sender
    if _sender is None:
        backend = settings.EMAIL_BACKEND
        if backend == "smtp":
            _sender = SmtpEmailSender()
        elif backend == "mock":
            _sender = MockEmailSender()
        else:
            _sender = ConsoleEmailSender()
    return _sender


def set_sender(sender: EmailSender | None) -> None:
    
    global _sender
    _sender = sender


def render(template_name: str, context: dict) -> RenderedEmail:
    
    from app.email.templates import TEMPLATES

    template = TEMPLATES.get(template_name)
    if template is None:
        raise KeyError(f"Unknown e-mail template: {template_name}")
    return template(context)
