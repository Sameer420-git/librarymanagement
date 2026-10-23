

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Any, Type

from sqlalchemy import Enum, JSON, Numeric
from sqlalchemy.types import TypeDecorator


def json_default(value: Any) -> Any:
    
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, PyEnum):
        return value.value
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serialisable")


def json_serializer(value: Any) -> str:
    return json.dumps(value, default=json_default)


class JSONPayload(TypeDecorator):
    

    impl = JSON
    cache_ok = True

    def bind_processor(self, dialect: Any):
        def process(value: Any) -> str | None:
            if value is None:
                return None
            return json_serializer(value)

        return process

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        return value


class Money(TypeDecorator):
    

    impl = Numeric(12, 2)
    cache_ok = True

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value)).quantize(Decimal("0.01"))

    def process_bind_param(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value)).quantize(Decimal("0.01"))


def enum_column(enum_class: Type[PyEnum], length: int = 64) -> Enum:
    
    return Enum(
        enum_class,
        native_enum=False,
        length=length,
        values_callable=lambda enum_cls: [member.value for member in enum_cls],
        validate_strings=True,
    )
