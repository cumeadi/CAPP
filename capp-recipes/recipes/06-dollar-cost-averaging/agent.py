import asyncio
import os
from capp import CAPPClient

class DCAAgent:
    def __init__(self, client: CAPPClient, sweep_pct: float, target_stablecoin: str, corridor: str):
        self.client = client
        self.sweep_pct = sweep_pct
        self.target_stablecoin = target_stablecoin
        self.corridor = corridor

    async def check_local_bank_balance(self):
        """Mock Open Banking / Mobile Money API"""
        # Imagine this calls Plaid, Mono, or Paystack
        return 500000.0  # e.g., NGN balance

    async def execute_daily_sweep(self):
        balance = await self.check_local_bank_balance()
        sweep_amount = balance * self.sweep_pct

        print(f"Current local bank balance: {balance:,.2f}")
        print(f"Sweeping {self.sweep_pct*100}% -> {sweep_amount:,.2f} local fiat.")

        try:
            # Route local fiat to stablecoin via CAPP
            res = await self.client.payments.send(
                amount=sweep_amount,
                from_currency="NGN",
                to_currency=self.target_stablecoin,
                recipient="self", # Internal wallet mapping
                corridor=self.corridor
            )
            print(f"DCA Sweep successful [{res.tx_id}]. Converted to {self.target_stablecoin}.")
        except Exception as e:
            print(f"Sweep failed: {e}")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        # Sweep 5% of NGN bank balance into cUSD_polygon daily
        agent = DCAAgent(
            client=client, 
            sweep_pct=0.05, 
            target_stablecoin="cUSD", 
            corridor="NG-US" 
        )
        
        await agent.execute_daily_sweep()

if __name__ == "__main__":
    asyncio.run(main())
