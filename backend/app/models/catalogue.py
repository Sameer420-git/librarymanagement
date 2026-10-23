

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.types import Money, enum_column
from app.models.enums import BookCopyStatus, CopyCondition

if TYPE_CHECKING:  
    from app.models.circulation import Loan, Reservation


class Publisher(Base, TimestampMixin):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    books: Mapped[list["Book"]] = relationship(back_populates="publisher")


class Author(Base, TimestampMixin):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    biography: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    books: Mapped[list["Book"]] = relationship(
        secondary="book_authors", viewonly=True, back_populates="authors"
    )
    book_author_links: Mapped[list["BookAuthor"]] = relationship(
        back_populates="author", cascade="all, delete-orphan", order_by="BookAuthor.author_order"
    )


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    books: Mapped[list["Book"]] = relationship(back_populates="category")


class BookAuthor(Base):
    

    __tablename__ = "book_authors"

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    author_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    book: Mapped["Book"] = relationship(back_populates="book_authors")
    author: Mapped["Author"] = relationship(back_populates="book_author_links")


class Book(Base, TimestampMixin):
    

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    subtitle: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    isbn: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True, index=True)
    isbn_10: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    publisher_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("publishers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    edition: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    publication_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(48), default="English", nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subjects: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    shelf_location: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    rack_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    total_copies: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_copies: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_reference_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    publisher: Mapped[Optional["Publisher"]] = relationship(back_populates="books")
    category: Mapped[Optional["Category"]] = relationship(back_populates="books")
    book_authors: Mapped[list["BookAuthor"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="BookAuthor.author_order"
    )
    authors: Mapped[list["Author"]] = relationship(
        secondary="book_authors", viewonly=True, back_populates="books", order_by="Author.name"
    )
    copies: Mapped[list["BookCopy"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_books_publisher_category", "publisher_id", "category_id"),
    )


class BookCopy(Base, TimestampMixin):
    

    __tablename__ = "book_copies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    accession_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    barcode: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    status: Mapped[BookCopyStatus] = mapped_column(
        enum_column(BookCopyStatus, 24),
        default=BookCopyStatus.AVAILABLE,
        nullable=False,
        index=True,
    )
    condition: Mapped[CopyCondition] = mapped_column(
        enum_column(CopyCondition, 24), default=CopyCondition.GOOD, nullable=False
    )
    acquisition_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Money, nullable=True)
    shelf_location: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    rack_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status_changed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    book: Mapped["Book"] = relationship(back_populates="copies")
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="copy", foreign_keys="Loan.copy_id"
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="copy")

    __table_args__ = (
        Index("ix_book_copies_book_status", "book_id", "status"),
    )
