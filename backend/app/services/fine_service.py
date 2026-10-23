

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.catalogue import BookCopy
from app.models.circulation import Fine, FinePayment, Loan
from app.models.enums import AuditAction, FineStatus, NotificationType, PaymentMethod
from app.models.user import User
from app.services.audit_service import log_action
from app.services.notification_service import queue_notification
from app.utils.helpers import money, utcnow


def get_fine(session: Session, fine_id: int, *, for_update: bool = False) -> Fine:
    stmt = (
        select(Fine)
        .where(Fine.id == fine_id)
        .options(
            selectinload(Fine.member),
            selectinload(Fine.payments),
            selectinload(Fine.loan).selectinload(Loan.copy).selectinload(BookCopy.book),
        )
    )
    if for_update:
        stmt = stmt.with_for_update()
    fine = session.execute(stmt).scalar_one_or_none()
    if fine is None:
        raise NotFoundError("Fine not found.")
    return fine


def fine_payload(fine: Fine) -> dict[str, Any]:
    book_title = None
    if fine.loan is not None and fine.loan.copy is not None and fine.loan.copy.book is not None:
        book_title = fine.loan.copy.book.title
    return {
        "id": fine.id,
        "member_id": fine.member_id,
        "loan_id": fine.loan_id,
        "amount": fine.amount,
        "amount_paid": fine.amount_paid,
        "outstanding": money(fine.amount - fine.amount_paid),
        "days_overdue": fine.days_overdue,
        "rate_per_day": fine.rate_per_day,
        "reason": fine.reason,
        "status": fine.status,
        "assessed_at": fine.assessed_at,
        "waived_at": fine.waived_at,
        "waiver_reason": fine.waiver_reason,
        "notes": fine.notes,
        "member_name": fine.member.full_name if fine.member else None,
        "member_email": fine.member.email if fine.member else None,
        "book_title": book_title,
        "payments": [
            {
                "id": payment.id,
                "fine_id": payment.fine_id,
                "amount": payment.amount,
                "method": payment.method,
                "reference": payment.reference,
                "paid_at": payment.paid_at,
                "notes": payment.notes,
                "recorded_by_name": None,
            }
            for payment in fine.payments
        ],
    }


def adjust_fine(
    session: Session, fine_id: int, actor: User, *, amount: Decimal | None, waive: bool, reason: str
) -> Fine:
    
    try:
        fine = get_fine(session, fine_id, for_update=True)
        if fine.status == FineStatus.CANCELLED:
            raise ValidationError("A cancelled fine cannot be adjusted.")

        previous_amount = fine.amount
        if waive:
            fine.amount = money(fine.amount_paid)
            fine.status = FineStatus.WAIVED
            fine.waived_at = utcnow()
            fine.waived_by_id = actor.id
            fine.waiver_reason = reason
        else:
            if amount is None:
                raise ValidationError("An amount is required to adjust a fine.")
            new_amount = money(amount)
            if new_amount < money(fine.amount_paid):
                raise ValidationError(
                    "The new amount cannot be lower than the amount already paid."
                )
            fine.amount = new_amount
            if fine.amount_paid >= new_amount:
                fine.status = FineStatus.PAID
            else:
                fine.status = FineStatus.PARTIALLY_PAID
            fine.notes = reason

        session.flush()
        log_action(
            session,
            AuditAction.FINE_ADJUSTED,
            actor=actor,
            entity_type="fine",
            entity_id=fine.id,
            summary=(
                f"Fine {fine.id} adjusted from {previous_amount} to {fine.amount} "
                f"({fine.status.value}) - {reason}"
            ),
        )
        session.commit()
        return get_fine(session, fine_id)
    except Exception:
        session.rollback()
        raise


def record_payment(
    session: Session,
    fine_id: int,
    actor: User,
    *,
    amount: Decimal,
    method: PaymentMethod,
    reference: str | None = None,
    notes: str | None = None,
) -> Fine:
    
    try:
        fine = get_fine(session, fine_id, for_update=True)
        if fine.status == FineStatus.WAIVED:
            raise ValidationError("A waived fine cannot receive a payment.")
        if fine.status == FineStatus.PAID:
            raise ValidationError("This fine is already fully paid.")

        outstanding = money(fine.amount - fine.amount_paid)
        payment_amount = money(amount)
        if payment_amount <= 0:
            raise ValidationError("The payment amount must be greater than zero.")
        if payment_amount > outstanding:
            raise ValidationError(
                f"The payment exceeds the outstanding balance of {outstanding}."
            )

        payment = FinePayment(
            fine_id=fine.id,
            amount=payment_amount,
            method=method,
            reference=reference,
            paid_at=utcnow(),
            recorded_by_id=actor.id,
            notes=notes,
        )
        session.add(payment)
        fine.amount_paid = money(fine.amount_paid + payment_amount)
        fine.status = (
            FineStatus.PAID if fine.amount_paid >= fine.amount else FineStatus.PARTIALLY_PAID
        )
        session.flush()

        member = fine.member
        if member is not None:
            queue_notification(
                session,
                user=member,
                notification_type=NotificationType.FINE_PAYMENT,
                template_name="fine_payment",
                context={
                    "name": member.first_name,
                    "amount": float(payment_amount),
                    "method": method.value,
                    "reference": reference or "-",
                    "paid_at": payment.paid_at,
                    "outstanding": float(money(fine.amount - fine.amount_paid)),
                },
                dedupe_key=f"fine_payment:{payment.id}",
            )

        log_action(
            session,
            AuditAction.FINE_PAYMENT_RECORDED,
            actor=actor,
            entity_type="fine",
            entity_id=fine.id,
            summary=f"Payment of {payment_amount} recorded against fine {fine.id}",
        )
        session.commit()
        return get_fine(session, fine_id)
    except Exception:
        session.rollback()
        raise


def list_fines(
    session: Session, params: dict[str, Any], *, restrict_to_member: int | None = None
) -> tuple[list[Fine], int]:
    stmt = select(Fine).options(
        selectinload(Fine.member),
        selectinload(Fine.payments),
        selectinload(Fine.loan).selectinload(Loan.copy).selectinload(BookCopy.book),
    )
    if restrict_to_member is not None:
        stmt = stmt.where(Fine.member_id == restrict_to_member)
    if params.get("member_id"):
        stmt = stmt.where(Fine.member_id == params["member_id"])
    if params.get("status"):
        stmt = stmt.where(Fine.status == params["status"])
    if params.get("outstanding_only"):
        stmt = stmt.where(
            Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID])
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Fine.assessed_at.desc())
    page = params.get("page", 1)
    page_size = params.get("page_size", 20)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(session.execute(stmt).scalars().unique()), total


def outstanding_total(session: Session, member_id: int | None = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
        Fine.status.in_([FineStatus.PENDING, FineStatus.PARTIALLY_PAID])
    )
    if member_id is not None:
        stmt = stmt.where(Fine.member_id == member_id)
    return money(session.execute(stmt).scalar_one())


def collected_total(session: Session, member_id: int | None = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(FinePayment.amount), 0))
    if member_id is not None:
        stmt = stmt.where(FinePayment.fine_id.in_(select(Fine.id).where(Fine.member_id == member_id)))
    return money(session.execute(stmt).scalar_one())
