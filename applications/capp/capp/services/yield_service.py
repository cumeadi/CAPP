"""
Yield Service for CAPP

Manages "Smart Sweep" logic to optimize idle treasury funds by moving them
to yield-generating protocols (Aave, etc.) and handling Just-in-Time (JIT)
liquidity requests.
"""

import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import structlog

from applications.capp.capp.config.settings import get_settings
from applications.capp.capp.core.redis import get_cache
from applications.capp.capp.models.payments import Chain, Currency

logger = structlog.get_logger(__name__)

class YieldService:
    """
    Yield Service
    
    Features:
    - Monitors idle funds in Hot Wallets.
    - Sweeps excess funds to Yield Protocols (Smart Sweep).
    - Handles Liquidity Requests (unwinding yield if needed).
    - Aggregates total treasury view.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = get_cache()
        self.logger = structlog.get_logger(__name__)
        
        # Configuration
        self.HOT_WALLET_BUFFER_PCT = Decimal("0.20") 
        self.MIN_SWEEP_AMOUNT = Decimal("1000.00")
        
        # Mock State for "Yield Protocol" balances (Aave strategy etc), NOT liquid balances
        # Structure: { "wallet_address": { "USDC": Decimal(...), ... } }
        self._mock_yield_balances = {
            "internal_hot_wallet": {
                "USDC": Decimal("50000.00"),
                "ETH": Decimal("10.0")
            }
        }

    async def _get_real_aptos_balance(self, address: str) -> Decimal:
        """Fetch real APT balance from Aptos Testnet Node"""
        try:
            import aiohttp
            from urllib.parse import quote
            node_url = self.settings.APTOS_NODE_URL
            
            # Resource for APT CoinStore
            resource_type = "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>"
            encoded_resource = quote(resource_type)
            
            async with aiohttp.ClientSession() as session:
                url = f"{node_url}/accounts/{address}/resource/{encoded_resource}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_balance = int(data["data"]["coin"]["value"])
                        # APT has 8 decimals
                        return Decimal(raw_balance) / Decimal(100_000_000)
                    elif response.status == 404:
                        return Decimal("0.0")
                    else:
                        self.logger.warning(f"Failed to fetch Aptos balance: {response.status}")
                        return Decimal("0.0")
        except Exception as e:
            self.logger.error(f"Error fetching Aptos balance: {str(e)}")
            return Decimal("0.0")
    
    async def get_total_treasury_balance(self, wallet_address: str = "internal_hot_wallet") -> Dict[str, Any]:
        """
        Get aggregated treasury balance (Hot + Yield) for a specific wallet.
        """
        # 1. Fetch REAL Aptos Balance if configured
        # Uses the configured address in settings.py if available, or a default/passed one
        target_aptos_addr = self.settings.APTOS_ACCOUNT_ADDRESS
        
        real_apt_balance = Decimal("0.0")
        if target_aptos_addr:
             real_apt_balance = await self._get_real_aptos_balance(target_aptos_addr)
        else:
             # Fallback to mock for demo if no ENV var set
             if wallet_address == "internal_hot_wallet":
                 real_apt_balance = Decimal("150.0")
             else:
                 real_apt_balance = Decimal("500.0")

        # Mock other balances as before
        if wallet_address == "internal_hot_wallet":
            hot_balance_usdc = Decimal("15000.00")
            hot_balance_eth = Decimal("2.5")
        else:
            hot_balance_usdc = Decimal("50000.00")
            hot_balance_eth = Decimal("10.0")
        
        # Get yield balances
        wallet_yield = self._mock_yield_balances.get(wallet_address, {})
        yield_balance_usdc = wallet_yield.get("USDC", Decimal("0"))
        yield_balance_eth = wallet_yield.get("ETH", Decimal("0"))
        # APT Yield is 0 for now as we don't have a real strategy connected yet
        yield_balance_apt = Decimal("0")
        
        return {
            "wallet_address": wallet_address,
            "total_usd_value": float(
                (hot_balance_usdc + yield_balance_usdc) + 
                ((hot_balance_eth + yield_balance_eth) * 2500) + 
                ((real_apt_balance + yield_balance_apt) * 10)
            ),
            "breakdown": {
                "USDC": {
                    "hot": float(hot_balance_usdc),
                    "yielding": float(yield_balance_usdc),
                    "total": float(hot_balance_usdc + yield_balance_usdc)
                },
                "ETH": {
                    "hot": float(hot_balance_eth),
                    "yielding": float(yield_balance_eth),
                    "total": float(hot_balance_eth + yield_balance_eth)
                },
                "APT": {
                    "hot": float(real_apt_balance),
                    "yielding": float(yield_balance_apt),
                    "total": float(real_apt_balance + yield_balance_apt)
                }
            }
        }

    async def optimize_wallet(self, wallet_address: str, config: Optional[Dict] = None):
        """
        SDK Hook: Analyze and optimize a specific wallet's idle funds.
        """
        self.logger.info(f"Optimizing wallet: {wallet_address}...", config=config)
        
        # Use provided config or default
        min_sweep = Decimal(str(config.get("min_sweep_amount", self.MIN_SWEEP_AMOUNT))) if config else self.MIN_SWEEP_AMOUNT
        buffer_pct = Decimal(str(config.get("buffer_pct", self.HOT_WALLET_BUFFER_PCT))) if config else self.HOT_WALLET_BUFFER_PCT

        # 1. Get Wallet Balance (Mocked based on address)
        # In production, this would use self.chain_client.get_balance(wallet_address)
        if wallet_address == "internal_hot_wallet":
            hot_balance = Decimal("15000.00") # Internal
        else:
            hot_balance = Decimal("50000.00") # External Client
            
        # 2. Get Current Yield Balance for this wallet
        wallet_yield = self._mock_yield_balances.get(wallet_address, {})
        yield_balance = wallet_yield.get("USDC", Decimal("0"))
        
        # 3. Calculate Target
        total_balance = hot_balance + yield_balance
        target_buffer = total_balance * buffer_pct
        excess = hot_balance - target_buffer
        
        if excess > min_sweep:
            self.logger.info(f"Smart Sweep Triggered for {wallet_address}: Found ${excess} excess.")
            await self._execute_sweep(wallet_address, excess, "USDC")
        else:
            self.logger.info(f"No sweep needed for {wallet_address}. Excess ${excess} < Min ${min_sweep}")

    async def _execute_sweep(self, wallet_address: str, amount: Decimal, currency: str):
        """Mock execution of sweeping funds to Aave for a specific wallet"""
        try:
            self.logger.info(f"Sweeping {amount} {currency} for {wallet_address} to Strategy (Aave V3)...")
            await asyncio.sleep(0.5)
            
            # Initialize wallet dict if not exists
            if wallet_address not in self._mock_yield_balances:
                self._mock_yield_balances[wallet_address] = {}
                
            current_yield = self._mock_yield_balances[wallet_address].get(currency, Decimal("0"))
            self._mock_yield_balances[wallet_address][currency] = current_yield + amount
            
            self.logger.info(f"Sweep completed for {wallet_address}. New Yield Balance: {self._mock_yield_balances[wallet_address][currency]}")
            
        except Exception as e:
            self.logger.error(f"Sweep Failure for {wallet_address}: {e}")

    async def request_liquidity(self, wallet_address: str, amount: Decimal, currency: str) -> bool:
        """
        Request liquidity for a specific wallet. Unwinds yield if needed.
        """
        # Mock hot balances
        if wallet_address == "internal_hot_wallet":
            hot_balance = Decimal("5000.00")
        else:
            hot_balance = Decimal("1000.00") # Simulating low liquid funds for external client to trigger unwind

        if hot_balance >= amount:
            return True
            
        shortfall = amount - hot_balance
        self.logger.warning(f"Insufficient Hot Liquidity for {wallet_address}. Shortfall: {shortfall}. Initiating Unwind...")
        
        wallet_yield = self._mock_yield_balances.get(wallet_address, {})
        yield_balance = wallet_yield.get(currency, Decimal("0"))
        
        if yield_balance < shortfall:
            self.logger.error(f"Critical: Insufficient Total Liquidity for {wallet_address}.")
            return False
            
        # Unwind
        self.logger.info(f"Unwinding {shortfall} {currency} for {wallet_address}...")
        await asyncio.sleep(1)
        
        self._mock_yield_balances[wallet_address][currency] -= shortfall
        self.logger.info(f"Liquidity Unwound for {wallet_address}.")
        return True
