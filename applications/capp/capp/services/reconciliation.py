
import structlog
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any

from applications.capp.capp.core.aptos import get_aptos_client
from applications.capp.capp.core.polygon import PolygonSettlementService
from applications.capp.capp.core.redis import get_redis_client, get_cache
from applications.capp.capp.config.settings import settings

logger = structlog.get_logger(__name__)

class ReconciliationError(Exception):
    pass

class ReconciliationService:
    """
    Watchdog service that verifies System Integrity.
    Compares Internal Ledger (DB/Redis) vs On-Chain State.
    """
    
    DRIFT_THRESHOLD = Decimal("0.0001") # 0.01%
    
    def __init__(self):
        self.redis = get_redis_client()
        self.cache = get_cache()
        self.aptos = get_aptos_client()
        self.polygon = PolygonSettlementService()

    async def get_internal_ledger_balance(self, chain: str) -> Decimal:
        """
        Mock: Fetch total user balances from DB for a specific chain.
        In a real system, this would be `SELECT SUM(balance) FROM wallets WHERE chain=...`
        """
        # For this demo, we assume the internal ledger should track X amount.
        # We'll use a Redis key 'ledger:total:{chain}' or return a mock value that 
        # is INTENTIONALLY usually correct but we can drift it for testing.
        
        ledger_key = f"ledger:total:{chain}"
        val = await self.cache.get(ledger_key)
        if val:
            return Decimal(str(val))
            
        # Default mock values if not set
        if chain == "APTOS":
            return Decimal("100.00") 
        elif chain == "POLYGON":
            return Decimal("2000.00")
        
        return Decimal("0")

    async def get_on_chain_balance(self, chain: str) -> Decimal:
        """
        Fetch real on-chain balance of the Treasury/Hot Wallet.
        """
        try:
            if chain == "APTOS":
                # We use the configured account
                addr = settings.APTOS_ACCOUNT_ADDRESS
                bal = await self.aptos.get_account_balance(addr)
                return Decimal(str(bal))
                
            elif chain == "POLYGON":
                # We use the configured polygon account (or a hardcoded one for MVP)
                # Check if attribute exists, else use default
                if hasattr(settings, "POLYGON_ACCOUNT_ADDRESS"):
                    addr = settings.POLYGON_ACCOUNT_ADDRESS
                else:
                    addr = "0x0"
                    
                # Check USDC
                usdc = await self.polygon.get_token_balance("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", addr)
                return Decimal(str(usdc))
                
        except Exception as e:
            logger.error("failed_to_fetch_chain_balance", chain=chain, error=str(e))
            raise ReconciliationError(f"Chain Fetch Error: {e}")
            
        return Decimal("0")

    async def check_integrity(self) -> Dict[str, Any]:
        """
        Run the reconciliation process.
        Returns a report.
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "HEALTHY",
            "checks": []
        }
        
        chains = ["APTOS", "POLYGON"]
        drift_detected = False
        
        for chain in chains:
            try:
                internal = await self.get_internal_ledger_balance(chain)
                on_chain = await self.get_on_chain_balance(chain)
                
                # Check Drift
                # Avoid division by zero
                if internal == 0:
                     diff_pct = Decimal("0") if on_chain == 0 else Decimal("1.0") # 100% drift if internal 0 but chain has funds
                else:
                    diff_pct = abs((on_chain - internal) / internal)
                
                check = {
                    "chain": chain,
                    "internal_balance": float(internal),
                    "on_chain_balance": float(on_chain),
                    "drift_pct": float(diff_pct),
                    "status": "OK"
                }
                
                if diff_pct > self.DRIFT_THRESHOLD:
                    check["status"] = "DRIFT_DETECTED"
                    drift_detected = True
                    self.trigger_alert(chain, internal, on_chain, diff_pct)
                    
                report["checks"].append(check)
                
            except Exception as e:
                report["checks"].append({
                    "chain": chain,
                    "error": str(e),
                    "status": "ERROR"
                })
        
        if drift_detected:
            report["status"] = "CRITICAL_DRIFT"
            
        return report

    def trigger_alert(self, chain: str, internal: Decimal, on_chain: Decimal, drift: Decimal):
        """
        Simulate a Webhook/PagerDuty alert.
        """
        msg = f"🚨 INTEGRITY BREACH: {chain} Drift > 0.01%! Internal: {internal}, Chain: {on_chain}, Drift: {drift:.2%}"
        logger.critical(msg)
        # requests.post(settings.SLACK_WEBHOOK, json={"text": msg})
