from decimal import Decimal
from typing import Dict, Tuple
from datetime import datetime
from pydantic import BaseModel

class RebalanceAction(BaseModel):
    should_rebalance: bool
    action_type: str = "NONE" # NONE, MARKET_SWAP, LIMIT_ORDER
    amount_needed: Decimal = Decimal("0")
    reason: str = ""

class AdaptiveLiquidityStrategy:
    """
    Adaptive Liquidity Strategy ("Smart Buffers")
    
    Dynamically adjusts liquidity thresholds based on volume usage.
    """
    
    def __init__(self, base_buffer: Decimal = Decimal("1000.0")):
        self.base_buffer = base_buffer
        self.volume_history: Dict[str, list] = {} # pool_id -> list of (timestamp, volume)

    def record_usage(self, pool_id: str, amount: Decimal):
        """Record usage volume to inform future predictions"""
        if pool_id not in self.volume_history:
            self.volume_history[pool_id] = []
        self.volume_history[pool_id].append((datetime.now(), amount))
        
        # Keep only last 24h of history
        # (Simplified implementation: just keep last 100 entries for demo)
        if len(self.volume_history[pool_id]) > 100:
            self.volume_history[pool_id].pop(0)

    def calculate_threshold(self, pool_id: str) -> Decimal:
        """
        Calculate dynamic minimum threshold
        Min_Threshold = MAX(Base_Limit, Average_Volume * 2)
        """
        history = self.volume_history.get(pool_id, [])
        if not history:
            return self.base_buffer
            
        total_volume = sum(item[1] for item in history)
        avg_volume = total_volume / len(history) if history else Decimal("0")
        
        # Heuristic: Keep buffer for 2x average usage
        dynamic_buffer = avg_volume * Decimal("2")
        
        return max(self.base_buffer, dynamic_buffer)

    def evaluate(self, pool_id: str, current_balance: Decimal) -> RebalanceAction:
        """Evaluate if rebalancing is needed"""
        min_threshold = self.calculate_threshold(pool_id)
        
        # Critical Level: Below Base Buffer -> Urgent
        if current_balance < self.base_buffer:
            needed = min_threshold - current_balance
            return RebalanceAction(
                should_rebalance=True,
                action_type="MARKET_SWAP",
                amount_needed=needed,
                reason=f"CRITICAL: Balance {current_balance} < Base Buffer {self.base_buffer}"
            )

        # Predictive Level: Below Dynamic Threshold -> Warning
        if current_balance < min_threshold:
            needed = min_threshold - current_balance
            return RebalanceAction(
                should_rebalance=True,
                action_type="LIMIT_ORDER", # Simulating a cheaper/slower rebalance
                amount_needed=needed,
                reason=f"PREDICTIVE: Balance {current_balance} < Smart Buffer {min_threshold}"
            )
            
        return RebalanceAction(should_rebalance=False)
