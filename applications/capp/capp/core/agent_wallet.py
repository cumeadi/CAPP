from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

class WalletTransaction(BaseModel):
    tx_id: str
    amount: Decimal
    recipient: str
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "COMPLETED"

class BudgetManager:
    """
    Manages spending limits for an agent.
    Resets daily.
    """
    def __init__(self, daily_limit: Decimal):
        self.daily_limit = daily_limit
        self.current_spend = Decimal("0")
        self.last_reset_date = date.today()

    def _check_reset(self):
        """Reset budget if new day"""
        today = date.today()
        if today > self.last_reset_date:
            self.current_spend = Decimal("0")
            self.last_reset_date = today

    def can_spend(self, amount: Decimal) -> bool:
        self._check_reset()
        if self.current_spend + amount > self.daily_limit:
            return False
        return True

    def record_spend(self, amount: Decimal):
        self._check_reset()
        self.current_spend += amount

class AgentWallet:
    """
    Petty Cash Wallet for Autonomous Agents.
    Allows agents to hold and spend small amounts of funds for operational costs (x402).
    """
    def __init__(self, agent_id: str, daily_limit: Decimal = Decimal("50.00")):
        self.agent_id = agent_id
        self.balance = Decimal("0")
        self.budget = BudgetManager(daily_limit)
        self.transactions: List[WalletTransaction] = []
        self.currency = "USDC" # Default currency

    def deposit(self, amount: Decimal, source: str = "Treasury"):
        """Deposit funds into the petty wallet"""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        
        self.balance += amount
        self.transactions.append(WalletTransaction(
            tx_id=f"dep_{len(self.transactions)}",
            amount=amount,
            recipient=self.agent_id,
            reason=f"Deposit from {source}",
            status="DEPOSIT"
        ))
        logger.info("Wallet Deposit", agent_id=self.agent_id, amount=str(amount), new_balance=str(self.balance))

    def spend(self, amount: Decimal, recipient: str, reason: str) -> WalletTransaction:
        """
        Attempt to spend funds.
        Checks:
        1. Sufficient Balance
        2. Daily Budget Limit
        """
        if amount <= 0:
             raise ValueError("Spend amount must be positive")

        # 1. Check Balance
        if self.balance < amount:
            raise ValueError(f"Insufficient funds. Balance: {self.balance}, Required: {amount}")

        # 2. Check Budget
        if not self.budget.can_spend(amount):
            raise ValueError(f"Daily budget exceeded. Limit: {self.budget.daily_limit}, Spent: {self.budget.current_spend}, Request: {amount}")

        # Execute Spend
        self.balance -= amount
        self.budget.record_spend(amount)
        
        tx = WalletTransaction(
            tx_id=f"tx_{len(self.transactions)}",
            amount=amount,
            recipient=recipient,
            reason=reason
        )
        self.transactions.append(tx)
        
        logger.info(
            "Wallet Spend", 
            agent_id=self.agent_id, 
            amount=str(amount), 
            recipient=recipient, 
            reason=reason,
            remaining_balance=str(self.balance)
        )
        
        return tx

    def get_status(self) -> Dict:
        """Return wallet status"""
        return {
            "agent_id": self.agent_id,
            "balance": str(self.balance),
            "currency": self.currency,
            "daily_limit": str(self.budget.daily_limit),
            "spent_today": str(self.budget.current_spend)
        }
