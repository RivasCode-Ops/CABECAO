from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_serializer


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    qty_on_hand: Decimal
    avg_cost: Decimal

    model_config = {"from_attributes": True}

    @field_serializer("qty_on_hand", "avg_cost")
    def _ser_dec(self, v: Decimal) -> str:
        return str(v)


class PurchaseLineIn(BaseModel):
    product_id: int = Field(gt=0)
    qty: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseCreate(BaseModel):
    occurred_on: date
    note: str | None = None
    lines: list[PurchaseLineIn] = Field(min_length=1)


class PurchaseLineOut(BaseModel):
    id: int
    product_id: int
    qty: Decimal
    unit_cost: Decimal

    model_config = {"from_attributes": True}

    @field_serializer("qty", "unit_cost")
    def _ser(self, v: Decimal) -> str:
        return str(v)


class PurchaseOut(BaseModel):
    id: int
    occurred_on: date
    note: str | None
    lines: list[PurchaseLineOut]

    model_config = {"from_attributes": True}


class SaleLineIn(BaseModel):
    product_id: int = Field(gt=0)
    qty: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class SaleCreate(BaseModel):
    occurred_on: date
    note: str | None = None
    lines: list[SaleLineIn] = Field(min_length=1)


class SaleLineOut(BaseModel):
    id: int
    product_id: int
    qty: Decimal
    unit_price: Decimal

    model_config = {"from_attributes": True}

    @field_serializer("qty", "unit_price")
    def _ser(self, v: Decimal) -> str:
        return str(v)


class SaleOut(BaseModel):
    id: int
    occurred_on: date
    note: str | None
    lines: list[SaleLineOut]

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    cash_balance: str
    inventory_balance: str
    products_count: int
    purchases_count: int
    sales_count: int
