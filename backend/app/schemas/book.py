

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import BookCopyStatus, CopyCondition
from app.schemas.common import ORMModel


class AuthorBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    biography: str | None = None
    nationality: str | None = None


class AuthorRead(ORMModel):
    id: int
    name: str
    biography: str | None = None
    nationality: str | None = None


class AuthorCreate(AuthorBase):
    pass


class PublisherRead(ORMModel):
    id: int
    name: str
    address: str | None = None
    contact_email: str | None = None
    website: str | None = None


class PublisherCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    contact_email: str | None = None
    website: str | None = None


class CategoryRead(ORMModel):
    id: int
    name: str
    description: str | None = None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    subtitle: str | None = Field(default=None, max_length=300)
    isbn: str | None = Field(default=None, max_length=32)
    isbn_10: str | None = Field(default=None, max_length=32)
    publisher_id: int | None = None
    publisher_name: str | None = Field(default=None, max_length=200)
    category_id: int | None = None
    category_name: str | None = Field(default=None, max_length=120)
    edition: str | None = Field(default=None, max_length=80)
    publication_year: int | None = Field(default=None, ge=1000, le=2200)
    language: str = Field(default="English", max_length=48)
    description: str | None = None
    keywords: str | None = Field(default=None, max_length=512)
    subjects: str | None = Field(default=None, max_length=512)
    cover_image_url: str | None = Field(default=None, max_length=512)
    department_id: int | None = None
    shelf_location: str | None = Field(default=None, max_length=80)
    rack_number: str | None = Field(default=None, max_length=32)
    is_reference_only: bool = False
    author_names: list[str] = Field(default_factory=list)
    author_ids: list[int] = Field(default_factory=list)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    subtitle: str | None = Field(default=None, max_length=300)
    isbn: str | None = Field(default=None, max_length=32)
    isbn_10: str | None = Field(default=None, max_length=32)
    publisher_id: int | None = None
    publisher_name: str | None = Field(default=None, max_length=200)
    category_id: int | None = None
    category_name: str | None = Field(default=None, max_length=120)
    edition: str | None = Field(default=None, max_length=80)
    publication_year: int | None = Field(default=None, ge=1000, le=2200)
    language: str | None = Field(default=None, max_length=48)
    description: str | None = None
    keywords: str | None = Field(default=None, max_length=512)
    subjects: str | None = Field(default=None, max_length=512)
    cover_image_url: str | None = Field(default=None, max_length=512)
    department_id: int | None = None
    shelf_location: str | None = Field(default=None, max_length=80)
    rack_number: str | None = Field(default=None, max_length=32)
    is_reference_only: bool | None = None
    is_active: bool | None = None
    author_names: list[str] | None = None
    author_ids: list[int] | None = None


class BookSummary(ORMModel):
    id: int
    title: str
    subtitle: str | None = None
    isbn: str | None = None
    edition: str | None = None
    publication_year: int | None = None
    language: str
    cover_image_url: str | None = None
    total_copies: int
    available_copies: int
    is_active: bool
    shelf_location: str | None = None
    rack_number: str | None = None
    publisher_name: str | None = None
    category_name: str | None = None
    authors: list[str] = Field(default_factory=list)


class BookDetail(BookSummary):
    isbn_10: str | None = None
    description: str | None = None
    keywords: str | None = None
    subjects: str | None = None
    department_id: int | None = None
    is_reference_only: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BookCopyBase(BaseModel):
    accession_number: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    condition: CopyCondition = CopyCondition.GOOD
    acquisition_date: date | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    shelf_location: str | None = Field(default=None, max_length=80)
    rack_number: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class BookCopyCreate(BookCopyBase):
    pass


class BookCopyUpdate(BaseModel):
    barcode: str | None = Field(default=None, max_length=64)
    condition: CopyCondition | None = None
    acquisition_date: date | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    shelf_location: str | None = Field(default=None, max_length=80)
    rack_number: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class BookCopyRead(ORMModel):
    id: int
    book_id: int
    accession_number: str
    barcode: str | None = None
    status: BookCopyStatus
    condition: CopyCondition
    acquisition_date: date | None = None
    price: Decimal | None = None
    shelf_location: str | None = None
    rack_number: str | None = None
    notes: str | None = None
    status_changed_at: datetime | None = None
    book_title: str | None = None
    active_loan_id: int | None = None
    active_loan_due_at: datetime | None = None


class CopyStatusUpdate(BaseModel):
    status: BookCopyStatus
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("status")
    @classmethod
    def _valid(cls, value: BookCopyStatus) -> BookCopyStatus:
        return value


class BookSearchParams(BaseModel):
    search: str | None = None
    category_id: int | None = None
    publisher_id: int | None = None
    department_id: int | None = None
    language: str | None = None
    available_only: bool = False
    include_inactive: bool = False
    sort_by: str = "title"
    sort_order: str = "asc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CopySearchParams(BaseModel):
    accession_number: str | None = None
    barcode: str | None = None
    book_id: int | None = None
    status: BookCopyStatus | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class InventoryAdjustmentRead(ORMModel):
    id: int
    copy_id: int
    previous_status: str
    new_status: str
    reason: str | None = None
    changed_by_id: int | None = None
    changed_at: datetime | None = None


class ImportPreviewRow(BaseModel):
    row_number: int
    data: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    duplicate: bool = False
