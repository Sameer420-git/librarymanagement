

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import settings

MONEY_QUANT = Decimal("0.01")





def get_timezone() -> ZoneInfo:
    
    try:
        return ZoneInfo(settings.LIBRARY_TIMEZONE)
    except Exception:
        return ZoneInfo("UTC")


def local_now() -> datetime:
    
    return datetime.now(get_timezone())


def local_today() -> date:
    return local_now().date()


def utcnow() -> datetime:
    
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=get_timezone()).astimezone(timezone.utc)
    return value.astimezone(timezone.utc)


def naive_utc(value: datetime | None) -> datetime | None:
    
    if value is None:
        return None
    aware = ensure_utc(value)
    return aware.replace(tzinfo=None) if aware else None


def ensure_utc(value: datetime | None) -> datetime | None:
    
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def local_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    aware = ensure_utc(value)
    return aware.astimezone(get_timezone()).date() if aware else None





def money(value: Decimal | float | int | str | None) -> Decimal:
    
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)





def offset_for(page: int, page_size: int) -> int:
    return max(0, (page - 1) * page_size)


def pagination_meta(page: int, page_size: int, total: int) -> dict[str, Any]:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }
