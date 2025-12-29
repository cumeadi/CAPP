from decimal import Decimal
from typing import Dict, Tuple, Any
from datetime import datetime
from pydantic import BaseModel

class RebalanceAction(BaseModel):
    should_rebalance: bool
    action_type: str = "NONE" # NONE, MARKET_SWAP, LIMIT_ORDER, HALT
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

class AIAdaptiveStrategy(AdaptiveLiquidityStrategy):
    """
    AI-Enhanced Liquidity Strategy
    
    Uses market risk analysis from the AI Brain to adjust buffers dynamically.
    """
    def __init__(self, base_buffer: Decimal = Decimal("1000.0")):
        super().__init__(base_buffer)
        
    def evaluate_with_ai(self, pool_id: str, current_balance: Decimal, ai_analysis: Dict[str, Any]) -> RebalanceAction:
        """
        Evaluate rebalancing leveraging AI Market Analysis.
        
        Risk Levels:
        - LOW: Normal operation.
        - MEDIUM: Increase buffer by 20%.
        - HIGH: Increase buffer by 50% and prefer LIMIT orders to avoid slippage, or HALT if extreme.
        """
        # 1. Get Standard Threshold
        base_threshold = self.calculate_threshold(pool_id)
        
        # 2. Apply AI Risk Multiplier
        risk_level = ai_analysis.get("risk_level", "UNKNOWN")
        recommendation = ai_analysis.get("recommendation", "HOLD")
        
        multiplier = Decimal("1.0")
        if risk_level == "MEDIUM":
            multiplier = Decimal("1.2")
        elif risk_level == "HIGH":
            multiplier = Decimal("1.5")
            
        adjusted_threshold = base_threshold * multiplier
        
        # 3. Check for HALT conditions
        if risk_level == "HIGH" and "HALT" in recommendation:
             return RebalanceAction(
                should_rebalance=False,
                action_type="HALT",
                amount_needed=Decimal("0"),
                reason=f"AI HALT: {ai_analysis.get('reasoning')}"
            )

        # 4. Evaluate against Adjusted Threshold
        status = super().evaluate(pool_id, current_balance)
        
        # If standard eval says rebalance, check if we need to modify the action based on AI
        if status.should_rebalance:
            # If risk is high, maybe force LIMIT order even if critical, to avoid bad execution? 
            # Or conversely, if risk is high, maybe we desperately need liquidity so MARKET SWAP is okay?
            # Let's say if Risk is High, we want to be CAREFUL, so we prefer LIMIT unless it's dangerously low.
            
            # Re-calculate needed with adjusted threshold
            if current_balance < adjusted_threshold:
                needed = adjusted_threshold - current_balance
                status.amount_needed = max(status.amount_needed, needed)
                status.reason += f" [AI Risk Adjustment: {risk_level}]"
                
        # If standard eval said NO rebalance, but we are below the AI adjusted threshold
        elif current_balance < adjusted_threshold:
             needed = adjusted_threshold - current_balance
             return RebalanceAction(
                should_rebalance=True,
                action_type="LIMIT_ORDER",
                amount_needed=needed,
                reason=f"AI PREDICTIVE: Balance {current_balance} < Risk-Adjusted Buffer {adjusted_threshold}"
            )
            
        return status
