

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.email.templates.base import callout, detail_table, layout, money, paragraph


@dataclass(slots=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


def _fmt_dt(value: datetime | None, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    if value is None:
        return "-"
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def _plain(text: str) -> str:
    return " ".join(text.split())





def welcome(context: dict[str, Any]) -> RenderedEmail:
    name = context.get("name", "there")
    body = (
        paragraph(f"Welcome to the College Library, {name}!")
        + paragraph(
            "Your library account has been created. You can now search the catalogue, "
            "reserve books and borrow copies from the circulation desk."
        )
        + detail_table(
            [
                ("Name", str(context.get("name", "-"))),
                ("E-mail", str(context.get("email", "-"))),
                ("Role", str(context.get("role", "-")).replace("_", " ").title()),
                ("Member ID", str(context.get("institutional_id") or "-")),
            ]
        )
    )
    text = _plain(
        f"Welcome to the College Library, {name}. Your library account has been created. "
        f"Role: {context.get('role', '-')}. E-mail: {context.get('email', '-')}."
    )
    return RenderedEmail(
        subject="Welcome to the College Library",
        html=layout("Welcome to the College Library", body, preheader="Your account is ready"),
        text=text,
    )


def email_verification(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph("Please confirm your e-mail address to activate library services.")
        + callout(
            "This verification link expires in "
            f"{context.get('expiry_hours', 24)} hours.",
            "info",
        )
    )
    text = "Please verify your e-mail address to activate your library account."
    return RenderedEmail(
        subject="Verify your library account e-mail",
        html=layout(
            "Verify your e-mail address",
            body,
            preheader="Confirm your address to activate your account",
            action_url=context.get("verification_url"),
            action_label="Verify e-mail address",
        ),
        text=text,
    )


def password_reset(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph("A password reset was requested for your library account.")
        + detail_table([("Requested for", str(context.get("email", "-")))])
        + callout(
            "This link can be used only once and expires in "
            f"{context.get('expiry_minutes', 30)} minutes. If you did not request this, "
            "you can safely ignore this e-mail.",
            "warning",
        )
    )
    text = (
        "A password reset was requested for your library account. "
        "The link can be used once and expires shortly."
    )
    return RenderedEmail(
        subject="Reset your library account password",
        html=layout(
            "Reset your password",
            body,
            preheader="A password reset was requested",
            action_url=context.get("reset_url"),
            action_label="Reset password",
        ),
        text=text,
    )





def book_issued(context: dict[str, Any]) -> RenderedEmail:
    due = _fmt_dt(context.get("due_at"))
    body = (
        paragraph(f"Hello {context.get('name', 'there')}, the book below has been issued to you.")
        + detail_table(
            [
                ("Title", str(context.get("title", "-"))),
                ("Author", str(context.get("authors") or "-")),
                ("Accession No.", str(context.get("accession_number", "-"))),
                ("Issued on", _fmt_dt(context.get("issued_at"))),
                ("Due on", due),
            ]
        )
        + callout(
            "Please return the book on or before the due date to avoid overdue fines.",
            "info",
        )
    )
    text = _plain(
        f"Book issued: {context.get('title')} (accession {context.get('accession_number')}). "
        f"Due on {due}."
    )
    return RenderedEmail(
        subject=f"Book issued: {context.get('title', 'Library book')}",
        html=layout("Book issued", body, preheader=f"Due on {due}"),
        text=text,
    )


def book_returned(context: dict[str, Any]) -> RenderedEmail:
    fine = context.get("fine_amount")
    rows = [
        ("Title", str(context.get("title", "-"))),
        ("Accession No.", str(context.get("accession_number", "-"))),
        ("Issued on", _fmt_dt(context.get("issued_at"))),
        ("Returned on", _fmt_dt(context.get("returned_at"))),
        ("Days overdue", str(context.get("overdue_days", 0))),
    ]
    body = paragraph(f"Hello {context.get('name', 'there')}, we have recorded your book return.")
    if fine:
        rows.append(("Fine assessed", money(fine, context.get("currency", "INR"))))
        body += callout(
            f"A fine of {money(fine, context.get('currency', 'INR'))} has been assessed. "
            "You can settle it at the circulation desk.",
            "warning",
        )
    else:
        body += callout("No fine was assessed for this return. Thank you!", "success")
    body += detail_table(rows)
    text = _plain(
        f"Return receipt: {context.get('title')} returned on {_fmt_dt(context.get('returned_at'))}."
    )
    return RenderedEmail(
        subject=f"Book returned: {context.get('title', 'Library book')}",
        html=layout("Return receipt", body, preheader="Your return has been recorded"),
        text=text,
    )


def book_due_soon(context: dict[str, Any]) -> RenderedEmail:
    days = context.get("days_remaining", 0)
    body = (
        paragraph(f"Hello {context.get('name', 'there')}, a book borrowed by you is due soon.")
        + detail_table(
            [
                ("Title", str(context.get("title", "-"))),
                ("Accession No.", str(context.get("accession_number", "-"))),
                ("Due on", _fmt_dt(context.get("due_at"))),
                ("Days remaining", str(days)),
            ]
        )
        + callout("You may renew this book from your account if it is eligible.", "info")
    )
    text = _plain(f"'{context.get('title')}' is due on {_fmt_dt(context.get('due_at'))}.")
    return RenderedEmail(
        subject=f"Due soon: {context.get('title', 'Library book')}",
        html=layout("Book due soon", body, preheader=f"Due in {days} day(s)"),
        text=text,
    )


def book_overdue(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph(
            f"Hello {context.get('name', 'there')}, the following book is overdue and "
            "an fine has been applied to your account."
        )
        + detail_table(
            [
                ("Title", str(context.get("title", "-"))),
                ("Accession No.", str(context.get("accession_number", "-"))),
                ("Due on", _fmt_dt(context.get("due_at"))),
                ("Days overdue", str(context.get("overdue_days", 0))),
                (
                    "Estimated fine",
                    money(context.get("fine_amount", 0), context.get("currency", "INR")),
                ),
            ]
        )
        + callout(
            "Please return or renew the book immediately to stop further fines accruing.",
            "danger",
        )
    )
    text = _plain(
        f"'{context.get('title')}' is {context.get('overdue_days', 0)} day(s) overdue. "
        "Please return it promptly."
    )
    return RenderedEmail(
        subject=f"Overdue: {context.get('title', 'Library book')}",
        html=layout("Book overdue", body, preheader="Overdue notice"),
        text=text,
    )





def reservation_available(context: dict[str, Any]) -> RenderedEmail:
    deadline = _fmt_dt(context.get("pickup_deadline"))
    body = (
        paragraph(
            f"Hello {context.get('name', 'there')}, the book you reserved is now ready for pickup."
        )
        + detail_table(
            [
                ("Title", str(context.get("title", "-"))),
                ("Author", str(context.get("authors") or "-")),
                ("Accession No.", str(context.get("accession_number", "-"))),
                ("Shelf location", str(context.get("shelf_location") or "-")),
                ("Pick up by", deadline),
            ]
        )
        + callout(
            "This copy is held for you until the deadline above. After that it is released "
            "to the next member in the queue.",
            "warning",
        )
    )
    text = _plain(f"'{context.get('title')}' is ready for pickup. Collect by {deadline}.")
    return RenderedEmail(
        subject=f"Reserved book ready: {context.get('title', 'Library book')}",
        html=layout("Your reservation is ready", body, preheader="Collect your reserved copy"),
        text=text,
    )


def reservation_expired(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph(
            f"Hello {context.get('name', 'there')}, your reservation was released because the "
            "hold period expired."
        )
        + detail_table(
            [
                ("Title", str(context.get("title", "-"))),
                ("Expired on", _fmt_dt(context.get("expired_at"))),
            ]
        )
        + paragraph("You can place a fresh reservation for this title at any time.")
    )
    text = _plain(f"Your reservation for '{context.get('title')}' has expired.")
    return RenderedEmail(
        subject=f"Reservation expired: {context.get('title', 'Library book')}",
        html=layout("Reservation expired", body, preheader="Your hold has been released"),
        text=text,
    )





def fine_assessed(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph(f"Hello {context.get('name', 'there')}, a fine has been assessed on your account.")
        + detail_table(
            [
                ("Title", str(context.get("title") or "-")),
                ("Days overdue", str(context.get("overdue_days", 0))),
                ("Rate per day", money(context.get("rate_per_day", 0), context.get("currency", "INR"))),
                ("Fine amount", money(context.get("amount", 0), context.get("currency", "INR"))),
                ("Outstanding", money(context.get("outstanding", 0), context.get("currency", "INR"))),
            ]
        )
        + callout("You can settle the fine at the circulation desk.", "warning")
    )
    text = _plain(
        f"A fine of {money(context.get('amount', 0), context.get('currency', 'INR'))} was assessed."
    )
    return RenderedEmail(
        subject="Library fine assessed",
        html=layout("Fine assessed", body, preheader="Fine notification"),
        text=text,
    )


def fine_payment(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph(f"Hello {context.get('name', 'there')}, your fine payment has been recorded.")
        + detail_table(
            [
                ("Amount received", money(context.get("amount", 0), context.get("currency", "INR"))),
                ("Payment method", str(context.get("method", "-")).replace("_", " ").title()),
                ("Reference", str(context.get("reference") or "-")),
                ("Paid on", _fmt_dt(context.get("paid_at"))),
                (
                    "Remaining balance",
                    money(context.get("outstanding", 0), context.get("currency", "INR")),
                ),
            ]
        )
    )
    text = _plain(
        f"Payment of {money(context.get('amount', 0), context.get('currency', 'INR'))} recorded."
    )
    return RenderedEmail(
        subject="Library fine payment received",
        html=layout("Payment received", body, preheader="Thank you for your payment"),
        text=text,
    )


def membership_expiring(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph(
            f"Hello {context.get('name', 'there')}, your library membership is about to expire."
        )
        + detail_table(
            [
                ("Membership type", str(context.get("membership_type", "-")).title()),
                ("Expires on", _fmt_dt(context.get("membership_expires"))),
                ("Days remaining", str(context.get("days_remaining", 0))),
            ]
        )
        + callout(
            "Renew your membership at the circulation desk to keep borrowing books.",
            "warning",
        )
    )
    text = _plain(
        f"Your library membership expires on {_fmt_dt(context.get('membership_expires'))}."
    )
    return RenderedEmail(
        subject="Library membership expiring soon",
        html=layout("Membership expiring", body, preheader="Renew your membership"),
        text=text,
    )


def membership_expired(context: dict[str, Any]) -> RenderedEmail:
    body = (
        paragraph(f"Hello {context.get('name', 'there')}, your library membership has expired.")
        + detail_table([("Expired on", _fmt_dt(context.get("membership_expires")))])
        + callout(
            "Please renew your membership to continue borrowing books.",
            "danger",
        )
    )
    text = _plain("Your library membership has expired. Please renew it.")
    return RenderedEmail(
        subject="Library membership expired",
        html=layout("Membership expired", body, preheader="Renew your membership"),
        text=text,
    )


def generic_system(context: dict[str, Any]) -> RenderedEmail:
    body = paragraph(str(context.get("message", "Notification from the College Library.")))
    return RenderedEmail(
        subject=str(context.get("subject", "Library notification")),
        html=layout(str(context.get("title", "Library notification")), body),
        text=_plain(str(context.get("message", ""))),
    )


TEMPLATES = {
    "welcome": welcome,
    "email_verification": email_verification,
    "password_reset": password_reset,
    "book_issued": book_issued,
    "book_returned": book_returned,
    "book_due_soon": book_due_soon,
    "book_overdue": book_overdue,
    "reservation_available": reservation_available,
    "reservation_expired": reservation_expired,
    "fine_assessed": fine_assessed,
    "fine_payment": fine_payment,
    "membership_expiring": membership_expiring,
    "membership_expired": membership_expired,
    "system": generic_system,
}
