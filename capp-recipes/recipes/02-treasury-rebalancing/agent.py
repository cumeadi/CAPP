import asyncio
import os
import json
from capp import CAPPClient

class TreasuryRebalancingAgent:
    def __init__(self, client: CAPPClient, target_allocation: dict, drift_threshold: float):
        self.client = client
        self.target_allocation = target_allocation
        self.drift_threshold = drift_threshold

    async def get_portfolio_snapshot(self):
        print("Fetching portfolio snapshot...")
        balances = await self.client.wallet.get_balance()
        # Mocking portfolio value logic for recipe demonstration
        total_value_usd = 100000.0
        
        # A real implementation would query FX rates for all balances
        # Here we mock current allocation
        current_allocation = {
            "cUSD_aptos": 0.30,      # Drifted from 40%
            "USDC_polygon": 0.45,   # Drifted from 35%
            "APT": 0.15,
            "ETH_starknet": 0.10
        }
        return total_value_usd, current_allocation

    def calculate_drift(self, current_allocation: dict):
        drifts = {}
        needs_rebalance = False
        
        for asset, target_pct in self.target_allocation.items():
            current_pct = current_allocation.get(asset, 0.0)
            drift = current_pct - target_pct
            drifts[asset] = drift
            if abs(drift) > self.drift_threshold:
                needs_rebalance = True
                print(f"Asset {asset} drifted by {drift*100:.2f}%. Target: {target_pct*100:.2f}%, Current: {current_pct*100:.2f}%")
                
        return needs_rebalance, drifts

    async def execute_rebalance(self, total_value_usd: float, drifts: dict):
        print("Executing rebalance operations...")
        for asset, drift_pct in drifts.items():
            if drift_pct > self.drift_threshold:
                sell_amount = total_value_usd * drift_pct
                print(f"Action: SELL {sell_amount:.2f} USD worth of {asset}")
                
            elif drift_pct < -self.drift_threshold:
                buy_amount = total_value_usd * abs(drift_pct)
                print(f"Action: BUY {buy_amount:.2f} USD worth of {asset}")
                
        # Mocking actual SDK calls for cross-chain rebalancing
        print("Rebalancing complete.")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    drift_threshold = float(os.getenv("DRIFT_THRESHOLD", "0.05"))
    target_allocation_raw = os.getenv("TARGET_ALLOCATION", '{"cUSD_aptos": 0.40, "USDC_polygon": 0.35, "APT": 0.15, "ETH_starknet": 0.10}')
    target_allocation = json.loads(target_allocation_raw)
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        agent = TreasuryRebalancingAgent(client, target_allocation, drift_threshold)
        
        total_value, current_allocation = await agent.get_portfolio_snapshot()
        needs_rebalance, drifts = agent.calculate_drift(current_allocation)
        
        if needs_rebalance:
            print("Portfolio drift exceeded threshold. Rebalancing...")
            await agent.execute_rebalance(total_value, drifts)
        else:
            print("Portfolio within target allocations.")

if __name__ == "__main__":
    asyncio.run(main())
