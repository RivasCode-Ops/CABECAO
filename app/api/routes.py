import math
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import ACC_CASH, ACC_INVENTORY
from app.database import get_session
from app.models import Product, Purchase, Sale
from app.models.accounting import JournalEntry, JournalLine
from app.schemas import (
    DashboardSummary,
    JournalEntryOut,
    JournalLineDetail,
    PaginatedJournalEntries,
    PaginatedPurchases,
    PaginatedSales,
    PeriodReport,
    ProductCreate,
    ProductOut,
    PurchaseCreate,
    PurchaseOut,
    SaleCreate,
    SaleOut,
)
from app.services.ledger import get_account_balance, get_account_by_code
from app.services.operations import load_purchase_with_lines, load_sale_with_lines, record_purchase, record_sale
from app.services.reports import profit_and_loss
from app.utils.money import money

router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _journal_entry_out(entry: JournalEntry) -> JournalEntryOut:
    lines_sorted = sorted(entry.lines, key=lambda ln: ln.id)
    lines = [
        JournalLineDetail(
            account_code=ln.account.code,
            account_name=ln.account.name,
            debit=str(money(ln.debit)),
            credit=str(money(ln.credit)),
        )
        for ln in lines_sorted
    ]
    return JournalEntryOut(
        id=entry.id,
        occurred_on=entry.occurred_on,
        memo=entry.memo,
        source=entry.source.value,
        ref_id=entry.ref_id,
        lines=lines,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(session: SessionDep) -> DashboardSummary:
    caixa = await get_account_by_code(session, ACC_CASH)
    est = await get_account_by_code(session, ACC_INVENTORY)
    if not caixa or not est:
        raise HTTPException(503, "Plano de contas não inicializado.")

    cash = money(await get_account_balance(session, caixa.id))
    inv = money(await get_account_balance(session, est.id))

    pc = await session.scalar(select(func.count()).select_from(Product))
    pp = await session.scalar(select(func.count()).select_from(Purchase))
    ps = await session.scalar(select(func.count()).select_from(Sale))

    return DashboardSummary(
        cash_balance=str(cash),
        inventory_balance=str(inv),
        products_count=int(pc or 0),
        purchases_count=int(pp or 0),
        sales_count=int(ps or 0),
    )


@router.get("/products", response_model=list[ProductOut])
async def list_products(session: SessionDep) -> list[Product]:
    """Produtos mais recentes primeiro (id decrescente)."""
    r = await session.execute(select(Product).order_by(Product.id.desc()))
    return list(r.scalars().all())


@router.post("/products", response_model=ProductOut)
async def create_product(data: ProductCreate, session: SessionDep) -> Product:
    exists = await session.execute(select(Product).where(Product.sku == data.sku))
    if exists.scalar_one_or_none():
        raise HTTPException(409, "SKU já cadastrado.")
    p = Product(sku=data.sku.strip(), name=data.name.strip())
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, session: SessionDep) -> Product:
    p = await session.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado.")
    return p


@router.post("/purchases", response_model=PurchaseOut)
async def create_purchase(data: PurchaseCreate, session: SessionDep) -> Purchase:
    lines = [(ln.product_id, ln.qty, ln.unit_cost) for ln in data.lines]
    try:
        purchase = await record_purchase(
            session,
            occurred_on=data.occurred_on,
            note=data.note,
            lines=lines,
        )
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        await session.rollback()
        raise HTTPException(503, str(e)) from e

    full = await load_purchase_with_lines(session, purchase.id)
    assert full is not None
    return full


@router.get("/purchases", response_model=PaginatedPurchases)
async def list_purchases(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: int | None = Query(None, description="Filtrar pelo ano da data do movimento"),
) -> PaginatedPurchases:
    """Lista compras: data mais recente primeiro; paginação e filtro por ano opcional."""
    count_q = select(func.count()).select_from(Purchase)
    q = select(Purchase)
    if year is not None:
        yf = extract("year", Purchase.occurred_on) == year
        count_q = count_q.where(yf)
        q = q.where(yf)

    total = int(await session.scalar(count_q) or 0)

    q = (
        q.order_by(Purchase.occurred_on.desc(), Purchase.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(selectinload(Purchase.lines))
    )
    r = await session.execute(q)
    items = list(r.scalars().unique().all())
    total_pages = math.ceil(total / page_size) if page_size else 0
    return PaginatedPurchases(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/purchases/{purchase_id}", response_model=PurchaseOut)
async def get_purchase(purchase_id: int, session: SessionDep) -> Purchase:
    p = await load_purchase_with_lines(session, purchase_id)
    if not p:
        raise HTTPException(404, "Compra não encontrada.")
    return p


@router.post("/sales", response_model=SaleOut)
async def create_sale(data: SaleCreate, session: SessionDep) -> Sale:
    lines = [(ln.product_id, ln.qty, ln.unit_price) for ln in data.lines]
    try:
        sale = await record_sale(
            session,
            occurred_on=data.occurred_on,
            note=data.note,
            lines=lines,
        )
        await session.commit()
    except ValueError as e:
        await session.rollback()
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        await session.rollback()
        raise HTTPException(503, str(e)) from e

    full = await load_sale_with_lines(session, sale.id)
    assert full is not None
    return full


@router.get("/sales", response_model=PaginatedSales)
async def list_sales(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    year: int | None = Query(None, description="Filtrar pelo ano da data do movimento"),
) -> PaginatedSales:
    """Lista vendas: data mais recente primeiro; paginação e filtro por ano opcional."""
    count_q = select(func.count()).select_from(Sale)
    q = select(Sale)
    if year is not None:
        yf = extract("year", Sale.occurred_on) == year
        count_q = count_q.where(yf)
        q = q.where(yf)

    total = int(await session.scalar(count_q) or 0)

    q = (
        q.order_by(Sale.occurred_on.desc(), Sale.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(selectinload(Sale.lines))
    )
    r = await session.execute(q)
    items = list(r.scalars().unique().all())
    total_pages = math.ceil(total / page_size) if page_size else 0
    return PaginatedSales(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/sales/{sale_id}", response_model=SaleOut)
async def get_sale(sale_id: int, session: SessionDep) -> Sale:
    s = await load_sale_with_lines(session, sale_id)
    if not s:
        raise HTTPException(404, "Venda não encontrada.")
    return s


@router.get("/reports/pl", response_model=PeriodReport)
async def report_pl(
    session: SessionDep,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
) -> PeriodReport:
    """Receita (créditos em Receita), CMV e lucro bruto no período, com margem % sobre receita."""
    if from_date > to_date:
        raise HTTPException(400, "Data inicial não pode ser maior que a final.")
    try:
        revenue, cogs, gross = await profit_and_loss(session, from_date, to_date)
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    margin_pct: str | None = None
    if revenue > 0:
        margin_pct = str(money((gross / revenue) * Decimal("100")))
    return PeriodReport(
        from_date=from_date,
        to_date=to_date,
        revenue=str(revenue),
        cogs=str(cogs),
        gross_profit=str(gross),
        margin_percent=margin_pct,
    )


@router.get("/journal", response_model=PaginatedJournalEntries)
async def list_journal(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
) -> PaginatedJournalEntries:
    """Livro-razão: lançamentos com linhas e contas (data decrescente)."""
    count_q = select(func.count()).select_from(JournalEntry)
    total = int(await session.scalar(count_q) or 0)

    q = (
        select(JournalEntry)
        .order_by(JournalEntry.occurred_on.desc(), JournalEntry.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(selectinload(JournalEntry.lines).selectinload(JournalLine.account))
    )
    r = await session.execute(q)
    rows = list(r.scalars().unique().all())
    items = [_journal_entry_out(e) for e in rows]
    total_pages = math.ceil(total / page_size) if page_size else 0
    return PaginatedJournalEntries(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
