from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import ACC_CASH, ACC_COGS, ACC_INVENTORY, ACC_REVENUE
from app.models import Product, Purchase, PurchaseLine, Sale, SaleLine
from app.models.accounting import JournalSource
from app.services.ledger import get_account_by_code, post_journal
from app.utils.money import money


async def _accounts(session: AsyncSession) -> tuple[int, int, int, int]:
    caixa = await get_account_by_code(session, ACC_CASH)
    est = await get_account_by_code(session, ACC_INVENTORY)
    rev = await get_account_by_code(session, ACC_REVENUE)
    cmv = await get_account_by_code(session, ACC_COGS)
    if not all([caixa, est, rev, cmv]):
        raise RuntimeError("Plano de contas incompleto. Rode o seed.")
    return caixa.id, est.id, rev.id, cmv.id


async def record_purchase(
    session: AsyncSession,
    *,
    occurred_on: date,
    note: str | None,
    lines: list[tuple[int, Decimal, Decimal]],
) -> Purchase:
    """
    lines: (product_id, qty, unit_cost)
    Lançamento: Dr Estoque / Cr Caixa (à vista).
    Atualiza custo médio do produto.
    """
    if not lines:
        raise ValueError("Compra sem linhas.")

    caixa_id, est_id, _, _ = await _accounts(session)

    purchase = Purchase(occurred_on=occurred_on, note=note)
    session.add(purchase)
    await session.flush()

    total = Decimal("0")
    for product_id, qty, unit_cost in lines:
        if qty <= 0 or unit_cost < 0:
            raise ValueError("Quantidade e custo devem ser válidos.")
        line_total = money(qty * unit_cost)
        total += line_total

        p = await session.get(Product, product_id)
        if not p:
            raise ValueError(f"Produto id={product_id} não encontrado.")

        old_q = p.qty_on_hand
        old_avg = p.avg_cost
        new_q = old_q + qty
        if new_q > 0:
            new_avg = (old_q * old_avg + qty * unit_cost) / new_q
        else:
            new_avg = Decimal("0")
        p.qty_on_hand = new_q
        p.avg_cost = new_avg

        session.add(
            PurchaseLine(
                purchase_id=purchase.id,
                product_id=product_id,
                qty=qty,
                unit_cost=unit_cost,
            )
        )

    total = money(total)
    await post_journal(
        session,
        occurred_on=occurred_on,
        memo=note or f"Compra #{purchase.id}",
        lines=[
            (est_id, total, Decimal("0")),
            (caixa_id, Decimal("0"), total),
        ],
        source=JournalSource.PURCHASE,
        ref_id=f"purchase:{purchase.id}",
    )
    return purchase


async def record_sale(
    session: AsyncSession,
    *,
    occurred_on: date,
    note: str | None,
    lines: list[tuple[int, Decimal, Decimal]],
) -> Sale:
    """
    lines: (product_id, qty, unit_price)
    Lançamentos: Dr Caixa / Cr Receita e Dr CMV / Cr Estoque.
    """
    if not lines:
        raise ValueError("Venda sem linhas.")

    caixa_id, est_id, rev_id, cmv_id = await _accounts(session)

    sale = Sale(occurred_on=occurred_on, note=note)
    session.add(sale)
    await session.flush()

    revenue = Decimal("0")
    cogs = Decimal("0")

    for product_id, qty, unit_price in lines:
        if qty <= 0 or unit_price < 0:
            raise ValueError("Quantidade e preço devem ser válidos.")
        p = await session.get(Product, product_id)
        if not p:
            raise ValueError(f"Produto id={product_id} não encontrado.")
        if p.qty_on_hand < qty:
            raise ValueError(f"Estoque insuficiente para {p.sku}: tem {p.qty_on_hand}, pedido {qty}.")

        line_revenue = money(qty * unit_price)
        unit_cogs = p.avg_cost
        line_cogs = money(qty * unit_cogs)

        revenue += line_revenue
        cogs += line_cogs

        p.qty_on_hand = p.qty_on_hand - qty

        session.add(
            SaleLine(
                sale_id=sale.id,
                product_id=product_id,
                qty=qty,
                unit_price=unit_price,
            )
        )

    revenue = money(revenue)
    cogs = money(cogs)

    await post_journal(
        session,
        occurred_on=occurred_on,
        memo=note or f"Venda #{sale.id}",
        lines=[
            (caixa_id, revenue, Decimal("0")),
            (rev_id, Decimal("0"), revenue),
            (cmv_id, cogs, Decimal("0")),
            (est_id, Decimal("0"), cogs),
        ],
        source=JournalSource.SALE,
        ref_id=f"sale:{sale.id}",
    )
    return sale


async def load_purchase_with_lines(session: AsyncSession, purchase_id: int) -> Purchase | None:
    q = (
        select(Purchase)
        .where(Purchase.id == purchase_id)
        .options(selectinload(Purchase.lines))
    )
    r = await session.execute(q)
    return r.scalar_one_or_none()


async def load_sale_with_lines(session: AsyncSession, sale_id: int) -> Sale | None:
    q = select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.lines))
    r = await session.execute(q)
    return r.scalar_one_or_none()
