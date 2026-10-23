

from __future__ import annotations

import logging
import os
import socket
import uuid

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


def deliver_notifications_job() -> None:
    
    from app.db.session import session_scope
    from app.services.notification_service import process_pending

    try:
        with session_scope() as session:
            stats = process_pending(session)
        if stats["claimed"]:
            logger.info(
                "Delivered notifications: sent=%s failed=%s", stats["sent"], stats["failed"]
            )
    except Exception:
        logger.exception("Notification delivery job failed")


def generate_reminders_job() -> None:
    
    from app.db.session import session_scope
    from app.jobs.reminders import generate_all_reminders
    from app.services.policy_service import get_policy

    try:
        with session_scope() as session:
            policy = get_policy(session)
            stats = generate_all_reminders(session, policy)
        if stats["total"]:
            logger.info("Queued reminders: %s", stats)
    except Exception:
        logger.exception("Reminder generation job failed")


def expire_reservations_job() -> None:
    
    from app.db.session import session_scope
    from app.services.reservation_service import expire_reservations

    try:
        with session_scope() as session:
            expired = expire_reservations(session)
        if expired:
            logger.info("Expired %s reservation(s)", expired)
    except Exception:
        logger.exception("Reservation expiry job failed")


def flag_overdue_loans_job() -> None:
    
    from app.db.session import session_scope
    from app.services.circulation_service import mark_overdue_loans

    try:
        with session_scope() as session:
            count = mark_overdue_loans(session)
        if count:
            logger.info("Flagged %s overdue loan(s)", count)
    except Exception:
        logger.exception("Overdue flagging job failed")


class SchedulerManager:
    

    def __init__(self) -> None:
        self.scheduler: BackgroundScheduler | None = None

    @property
    def enabled(self) -> bool:
        return settings.SCHEDULER_ENABLED

    def start(self) -> None:
        if not self.enabled:
            logger.info("Scheduler disabled by configuration.")
            return
        if self.scheduler is not None:
            return

        scheduler = BackgroundScheduler(
            timezone=settings.LIBRARY_TIMEZONE,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            },
        )

        scheduler.add_job(
            deliver_notifications_job,
            IntervalTrigger(minutes=settings.SCHEDULER_INTERVAL_MINUTES),
            id="deliver_notifications",
            name="Deliver queued e-mail notifications",
            replace_existing=True,
        )
        scheduler.add_job(
            generate_reminders_job,
            IntervalTrigger(minutes=30),
            id="generate_reminders",
            name="Generate due / overdue / membership reminders",
            replace_existing=True,
        )
        scheduler.add_job(
            expire_reservations_job,
            IntervalTrigger(minutes=10),
            id="expire_reservations",
            name="Expire unclaimed reservations",
            replace_existing=True,
        )
        scheduler.add_job(
            flag_overdue_loans_job,
            IntervalTrigger(minutes=15),
            id="flag_overdue_loans",
            name="Flag overdue loans",
            replace_existing=True,
        )

        scheduler.start()
        self.scheduler = scheduler
        logger.info(
            "Scheduler started (worker=%s, timezone=%s)", WORKER_ID, settings.LIBRARY_TIMEZONE
        )

    def shutdown(self) -> None:
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            logger.info("Scheduler stopped")


scheduler_manager = SchedulerManager()
