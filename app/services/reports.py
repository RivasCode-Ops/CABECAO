from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACC_COGS, ACC_REVENUE
from app.models.accounting import JournalEntry, JournalLine
from app.services.ledger import get_account_by_code
from app.utils.money import money


async def profit_and_loss(
    session: AsyncSession, from_date: date, to_date: date
) -> tuple[Decimal, Decimal, Decimal]:
    """Receita (créditos em Receita), CMV (débitos em CMV) e lucro bruto no período (razão)."""
    rev_acc = await get_account_by_code(session, ACC_REVENUE)
    cogs_acc = await get_account_by_code(session, ACC_COGS)
    if not rev_acc or not cogs_acc:
        raise RuntimeError("Contas de receita/CMV não encontradas.")

    rev_q = (
        select(func.coalesce(func.sum(JournalLine.credit), 0))
        .select_from(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .where(JournalLine.account_id == rev_acc.id)
        .where(JournalEntry.occurred_on >= from_date)
        .where(JournalEntry.occurred_on <= to_date)
    )
    revenue = money(Decimal(str(await session.scalar(rev_q) or 0)))

    cogs_q = (
        select(func.coalesce(func.sum(JournalLine.debit), 0))
        .select_from(JournalLine)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
        .where(JournalLine.account_id == cogs_acc.id)
        .where(JournalEntry.occurred_on >= from_date)
        .where(JournalEntry.occurred_on <= to_date)
    )
    cogs = money(Decimal(str(await session.scalar(cogs_q) or 0)))

    gross = money(revenue - cogs)
    return revenue, cogs, gross
