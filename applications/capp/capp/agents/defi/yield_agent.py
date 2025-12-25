
import asyncio
import uuid
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field

from applications.capp.capp.agents.base import BasePaymentAgent, AgentConfig, AgentState
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentResult, Chain
from applications.capp.capp.services.executor import ExecutorService
from applications.capp.capp.config.settings import get_settings

logger = structlog.get_logger(__name__)

class YieldStrategy(BaseModel):
    name: str
    protocol: str # e.g. "AAVE_V3"
    asset: str # e.g. "USDC"
    target_chain: Chain
    min_idle_amount: Decimal = Decimal("1000.00") # Min balance to keep liquid
    
class YieldAgentConfig(AgentConfig):
    agent_type: str = "yield_optimization"
    check_interval_seconds: int = 600 # Check every 10 mins
    strategies: List[YieldStrategy] = []

class YieldAgent(BasePaymentAgent):
    """
    Autonomous Agent that optimizes idle liquidity on L2 chains.
    
    Logic:
    1. Monitor Balances on Arbitrum / Base.
    2. If Balance > Threshold (e.g. 1000 USDC), deposit excess to Aave.
    3. If Payment Needed > Liquid Balance, withdraw just-in-time.
    """
    
    def __init__(self, config: YieldAgentConfig):
        super().__init__(config)
        self.executor = ExecutorService() # "The Muscle"
        self.strategies = config.strategies
        self._is_running = False
        
    async def start(self):
        """Start the background monitoring loop"""
        await super().start()
        self._is_running = True
        asyncio.create_task(self._monitoring_loop())
        
    async def stop(self):
        self._is_running = False
        await super().stop()

    async def _monitoring_loop(self):
        """Periodic loop to check balances and rebalance"""
        self.logger.info("Yield Optimization Loop Started")
        while self._is_running:
            try:
                await self.check_and_optimize()
            except Exception as e:
                self.logger.error("Error in yield optimization loop", error=str(e))
                
            await asyncio.sleep(self.config.check_interval_seconds)

    async def check_and_optimize(self):
        """Core logic: Check balances and apply strategies"""
        self.logger.info("Checking idle liquidity...")
        
        for strategy in self.strategies:
            # 1. Check Liquid Balance (Mocked for now)
            liquid_balance = await self._get_balance(strategy.target_chain, strategy.asset)
            current_apr = await self.executor.get_yield_apr(strategy.target_chain)
            
            self.logger.info(
                "Market Info", 
                chain=strategy.target_chain, 
                balance=liquid_balance, 
                apr=current_apr
            )
            
            # 2. Optimization Decision
            # If we have excess liquidity > min_idle_amount, Supply it.
            # Example: Have 5000, Min is 1000 -> Supply 4000.
            excess_liquidity = liquid_balance - strategy.min_idle_amount
            
            if excess_liquidity > 0:
                self.logger.info(f"Found excess liquidity: ${excess_liquidity}. Optimizing...")
                await self.executor.supply_to_aave(strategy.target_chain, excess_liquidity)
                
    async def ensure_liquidity_for_payment(self, payment: CrossBorderPayment, required_chain: Chain):
        """
        Called by RouteOptimizationAgent/PaymentOrchestrator before execution.
        If liquid balance is insufficient, withdraw from Aave.
        """
        required_amount = payment.amount
        liquid_balance = await self._get_balance(required_chain, "USDC")
        
        if liquid_balance < required_amount:
            shortfall = required_amount - liquid_balance
            self.logger.warning(f"Liquidity Shortfall for Payment: ${shortfall}. Withdrawing from Yield...")
            
            # Withdraw Just-in-Time
            await self.executor.withdraw_from_aave(required_chain, shortfall)
            return True
        
        return True

    async def _get_balance(self, chain: Chain, asset: str) -> Decimal:
        """
        Mock Balance Fetcher. 
        In production, calls ChainMetricsService or Node.
        """
        # Return a mock value that triggers optimization for new chains
        if chain == Chain.ARBITRUM:
            return Decimal("2500.00") # Triggers optimization (2500 > 1000)
        elif chain == Chain.BASE:
            return Decimal("800.00") # No action
            
        return Decimal("0.00")

    # Required Abstract Methods
    async def process_payment(self, payment: CrossBorderPayment) -> PaymentResult:
        # Yield Agent doesn't process payments directly, it supports them.
        return PaymentResult(success=True, payment_id=payment.payment_id, status="completed", message="Yield Op")

    async def validate_payment(self, payment: CrossBorderPayment) -> bool:
        return True
