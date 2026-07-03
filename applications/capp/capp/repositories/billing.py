"""
Async repository for developer billing accounts and API keys.

Follows the same session-scoped pattern as repositories/user.py —
instantiate with an AsyncSession from get_db(), never hold state between calls.
"""

from decimal import Decimal
from typing import Optional
from uuid import uuid4

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import DeveloperAccount, DeveloperApiKey

logger = structlog.get_logger(__name__)


class BillingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    async def create_account(self, name: str, initial_balance: float = 0.0) -> DeveloperAccount:
        account_id = f"acc_{uuid4().hex[:8]}"
        account = DeveloperAccount(
            account_id=account_id,
            name=name,
            balance_usd=Decimal(str(initial_balance)),
        )
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        logger.info("developer_account_created", name=name, account_id=account_id)
        return account

    async def get_account(self, account_id: str) -> Optional[DeveloperAccount]:
        result = await self.session.execute(
            select(DeveloperAccount).where(DeveloperAccount.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def deduct_credits(self, account_id: str, amount: Decimal) -> DeveloperAccount:
        account = await self.get_account(account_id)
        if not account:
            raise ValueError("Account not found")
        if account.balance_usd < amount:
            raise ValueError(
                f"Insufficient funds. Balance: {account.balance_usd}, Charge: {amount}"
            )
        new_balance = account.balance_usd - amount
        await self.session.execute(
            update(DeveloperAccount)
            .where(DeveloperAccount.account_id == account_id)
            .values(balance_usd=new_balance)
        )
        await self.session.commit()
        account.balance_usd = new_balance
        logger.info("credits_deducted", account_id=account_id, amount=str(amount), new_balance=str(new_balance))
        return account

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------

    async def create_api_key(self, account_id: str) -> str:
        account = await self.get_account(account_id)
        if not account:
            raise ValueError("Account not found")
        key = f"pk_live_{uuid4().hex[:16]}"
        api_key = DeveloperApiKey(key=key, account_id=account_id)
        self.session.add(api_key)
        await self.session.commit()
        logger.info("api_key_created", account_id=account_id)
        return key

    async def get_api_key(self, key: str) -> Optional[DeveloperApiKey]:
        result = await self.session.execute(
            select(DeveloperApiKey).where(DeveloperApiKey.key == key)
        )
        return result.scalar_one_or_none()

    async def authorize(self, key: str) -> str:
        """Validate an API key. Returns account_id if valid; raises ValueError otherwise."""
        api_key = await self.get_api_key(key)
        if not api_key:
            raise ValueError("Invalid API key")
        if not api_key.is_active:
            raise ValueError("API key is inactive")
        return api_key.account_id

    async def check_credits(self, account_id: str, estimated_cost: Decimal) -> bool:
        account = await self.get_account(account_id)
        if not account:
            return False
        if account.balance_usd < estimated_cost:
            logger.warning(
                "insufficient_credits",
                account_id=account_id,
                balance=str(account.balance_usd),
                required=str(estimated_cost),
            )
            return False
        return True

    async def revoke_api_key(self, key: str) -> bool:
        from datetime import datetime
        result = await self.session.execute(
            update(DeveloperApiKey)
            .where(DeveloperApiKey.key == key)
            .values(is_active=False, revoked_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0
