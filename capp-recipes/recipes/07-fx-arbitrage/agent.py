import asyncio
import os
import time
from capp import CAPPClient

class FXArbitrageAgent:
    def __init__(self, client: CAPPClient, base_amount: float, corridors: list):
        self.client = client
        self.base_amount = base_amount
        self.corridors = corridors  # e.g. ["NG-KE", "KE-GH", "GH-NG"]

    async def check_circular_arbitrage(self):
        """Mock circular routing check over NGN -> KES -> GHS -> NGN"""
        print(f"[{time.strftime('%H:%M:%S')}] Scanning rates for circular path: {' -> '.join(self.corridors)}")
        
        # In reality, this queries client.routing.get_fx_rate() for each leg
        # Mocking an artificial spread opportunity:
        simulated_yield = self.base_amount * 1.015  # 1.5% profit
        
        if simulated_yield > self.base_amount:
            profit = simulated_yield - self.base_amount
            print(f"💡 Arbritrage gap found! Estimated profit: {profit:.2f} USD")
            return True, profit
        
        return False, 0.0

    async def execute_trades(self, profit_estimate: float):
        print("Executing instantaneous circular payment path...")
        try:
            # First leg
            res1 = await self.client.payments.send(
                amount=self.base_amount,
                from_currency="NGN", to_currency="KES",
                recipient="self_ke", corridor="NG-KE"
            )
            # Second leg
            res2 = await self.client.payments.send(
                amount=self.base_amount * 110, # Mock converted amt
                from_currency="KES", to_currency="GHS",
                recipient="self_gh", corridor="KE-GH"
            )
            # Third leg ...
            
            print(f"Trade cycle complete. Profit captured ~ {profit_estimate:.2f} USD")
            print(f"Tx sequence: [{res1.tx_id}, {res2.tx_id}]")
        except Exception as e:
            print(f"Arbitrage execution failed / slipped: {e}")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        # Looking for a 3-way circular trade starting with $10,000 NGN equivalent
        agent = FXArbitrageAgent(
            client=client, 
            base_amount=10000.0, 
            corridors=["NG-KE", "KE-GH", "GH-NG"]
        )
        
        # Scan for 3 intervals for demonstration
        for _ in range(3):
            found, profit = await agent.check_circular_arbitrage()
            if found:
                await agent.execute_trades(profit)
                break
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
