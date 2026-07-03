"""
BillingService — thin async façade over BillingRepository.

Callers should inject an AsyncSession (via FastAPI's Depends(get_db) or by
passing the session from the enclosing endpoint/service).  The singleton
pattern is gone; instantiate per-request like any other session-scoped service.

    billing = BillingService(db)
    account_id = await billing.authorize(api_key)
"""

import structlog
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.billing import BillingRepository
from ..core.database import DeveloperAccount

logger = structlog.get_logger(__name__)


class BillingService:
    def __init__(self, session: AsyncSession):
        self._repo = BillingRepository(session)

    async def create_account(self, name: str, initial_balance: float = 0.0) -> DeveloperAccount:
        return await self._repo.create_account(name, initial_balance)

    async def create_api_key(self, account_id: str) -> str:
        return await self._repo.create_api_key(account_id)

    async def authorize(self, api_key: str) -> str:
        """Returns account_id for a valid, active key; raises ValueError otherwise."""
        return await self._repo.authorize(api_key)

    async def check_credits(self, account_id: str, estimated_cost: Decimal) -> bool:
        return await self._repo.check_credits(account_id, estimated_cost)

    async def deduct_credits(self, account_id: str, amount: Decimal) -> None:
        await self._repo.deduct_credits(account_id, amount)
