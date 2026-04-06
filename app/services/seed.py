from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACC_CASH, ACC_COGS, ACC_INVENTORY, ACC_REVENUE
from app.models import Account, AccountType


async def seed_chart_accounts(session: AsyncSession) -> None:
    r = await session.execute(select(func.count()).select_from(Account))
    if (r.scalar() or 0) > 0:
        return

    rows = [
        (ACC_CASH, "Caixa", AccountType.ASSET),
        (ACC_INVENTORY, "Estoque de mercadorias", AccountType.ASSET),
        (ACC_REVENUE, "Receita de vendas", AccountType.REVENUE),
        (ACC_COGS, "Custo das mercadorias vendidas (CMV)", AccountType.EXPENSE),
    ]
    for code, name, acc_type in rows:
        session.add(Account(code=code, name=name, acc_type=acc_type))
    await session.flush()
