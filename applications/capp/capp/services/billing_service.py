
import structlog
from typing import Dict, Optional
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime
import uuid

logger = structlog.get_logger(__name__)

class ApiKey(BaseModel):
    key: str
    account_id: str
    active: bool = True
    created_at: datetime = datetime.now()

class DeveloperAccount(BaseModel):
    account_id: str
    name: str
    balance_usd: Decimal = Decimal("0.00")
    api_keys: Dict[str, ApiKey] = {}

class BillingService:
    _instance: Optional['BillingService'] = None
    
    def __init__(self):
        # In-memory storage for MVP
        self.accounts: Dict[str, DeveloperAccount] = {}
        self.api_key_index: Dict[str, str] = {} # Map key -> account_id
        self.logger = structlog.get_logger(__name__)

    @classmethod
    def get_instance(cls) -> 'BillingService':
        if cls._instance is None:
            cls._instance = BillingService()
        return cls._instance

    def create_account(self, name: str, initial_balance: float = 0.0) -> DeveloperAccount:
        account_id = f"acc_{uuid.uuid4().hex[:8]}"
        account = DeveloperAccount(
            account_id=account_id,
            name=name,
            balance_usd=Decimal(str(initial_balance))
        )
        self.accounts[account_id] = account
        self.logger.info(f"Created developer account: {name} ({account_id})")
        return account

    def create_api_key(self, account_id: str) -> str:
        if account_id not in self.accounts:
            raise ValueError("Account not found")
        
        key = f"pk_live_{uuid.uuid4().hex[:16]}"
        api_key = ApiKey(key=key, account_id=account_id)
        
        self.accounts[account_id].api_keys[key] = api_key
        self.api_key_index[key] = account_id
        
        self.logger.info(f"Generated API Key for account {account_id}")
        return key

    def authorize(self, api_key: str) -> str:
        """
        Validate API Key. Returns account_id if valid.
        Raises ValueError if invalid.
        """
        if api_key not in self.api_key_index:
            raise ValueError("Invalid API Key")
        
        account_id = self.api_key_index[api_key]
        account = self.accounts[account_id]
        
        if not account.api_keys[api_key].active:
            raise ValueError("API Key is inactive")
            
        return account_id

    def check_credits(self, account_id: str, estimated_cost: Decimal) -> bool:
        account = self.accounts.get(account_id)
        if not account:
            return False
        
        if account.balance_usd < estimated_cost:
            self.logger.warning(f"Insufficient funds for {account.name}. Balance: {account.balance_usd}, Required: {estimated_cost}")
            return False
            
        return True

    def deduct_credits(self, account_id: str, amount: Decimal):
        account = self.accounts.get(account_id)
        if not account:
            raise ValueError("Account not found")
            
        if account.balance_usd < amount:
            raise ValueError(f"Insufficient funds. Balance: {account.balance_usd}, Charge: {amount}")
            
        account.balance_usd -= amount
        self.logger.info(f"Charged {amount} USD to {account.name}. New Balance: {account.balance_usd}")
