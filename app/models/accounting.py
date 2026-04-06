import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountType(str, enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class JournalSource(str, enum.Enum):
    MANUAL = "MANUAL"
    SALE = "SALE"
    PURCHASE = "PURCHASE"
    ADJUSTMENT = "ADJUSTMENT"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    acc_type: Mapped[AccountType] = mapped_column(Enum(AccountType, name="account_type"))


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[JournalSource] = mapped_column(
        Enum(JournalSource, name="journal_source"), default=JournalSource.MANUAL
    )
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    lines: Mapped[list["JournalLine"]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["Account"] = relationship()
