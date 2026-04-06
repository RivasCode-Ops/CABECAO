from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants import ACC_CASH, ACC_INVENTORY
from app.database import get_session
from app.models import Product, Purchase, Sale
from app.schemas import (
    DashboardSummary,
    ProductCreate,
    ProductOut,
    PurchaseCreate,
    PurchaseOut,
    SaleCreate,
    SaleOut,
)
from app.services.ledger import get_account_balance, get_account_by_code
from app.services.operations import load_purchase_with_lines, load_sale_with_lines, record_purchase, record_sale
router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]


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
    r = await session.execute(select(Product).order_by(Product.sku))
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


@router.get("/purchases", response_model=list[PurchaseOut])
async def list_purchases(session: SessionDep) -> list[Purchase]:
    q = (
        select(Purchase)
        .order_by(Purchase.occurred_on.desc(), Purchase.id.desc())
        .options(selectinload(Purchase.lines))
    )
    r = await session.execute(q)
    return list(r.scalars().unique().all())


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


@router.get("/sales", response_model=list[SaleOut])
async def list_sales(session: SessionDep) -> list[Sale]:
    q = (
        select(Sale)
        .order_by(Sale.occurred_on.desc(), Sale.id.desc())
        .options(selectinload(Sale.lines))
    )
    r = await session.execute(q)
    return list(r.scalars().unique().all())


@router.get("/sales/{sale_id}", response_model=SaleOut)
async def get_sale(sale_id: int, session: SessionDep) -> Sale:
    s = await load_sale_with_lines(session, sale_id)
    if not s:
        raise HTTPException(404, "Venda não encontrada.")
    return s
