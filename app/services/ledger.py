from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, JournalEntry, JournalLine, JournalSource


async def assert_balanced_lines(lines: Sequence[tuple[int, Decimal, Decimal]]) -> None:
    total_debit = sum((d for _, d, _ in lines), Decimal("0"))
    total_credit = sum((c for _, _, c in lines), Decimal("0"))
    if total_debit != total_credit:
        raise ValueError("Lançamento contábil não balanceado (débito ≠ crédito).")


async def post_journal(
    session: AsyncSession,
    *,
    occurred_on: date,
    memo: str | None,
    lines: list[tuple[int, Decimal, Decimal]],
    source: JournalSource = JournalSource.MANUAL,
    ref_id: str | None = None,
) -> JournalEntry:
    await assert_balanced_lines(lines)
    entry = JournalEntry(occurred_on=occurred_on, memo=memo, source=source, ref_id=ref_id)
    session.add(entry)
    await session.flush()
    for account_id, debit, credit in lines:
        session.add(
            JournalLine(entry_id=entry.id, account_id=account_id, debit=debit, credit=credit)
        )
    return entry


async def get_account_balance(session: AsyncSession, account_id: int) -> Decimal:
    """Saldo: débitos - créditos (convênio para ativos/despesas positivos com débito)."""
    q = select(JournalLine.debit, JournalLine.credit).where(JournalLine.account_id == account_id)
    result = await session.execute(q)
    debit_sum = Decimal("0")
    credit_sum = Decimal("0")
    for d, c in result.all():
        debit_sum += d or Decimal("0")
        credit_sum += c or Decimal("0")
    return debit_sum - credit_sum


async def get_account_by_code(session: AsyncSession, code: str) -> Account | None:
    r = await session.execute(select(Account).where(Account.code == code))
    return r.scalar_one_or_none()
