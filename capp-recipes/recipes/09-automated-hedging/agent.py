import asyncio
import os
from datetime import datetime, timedelta
from capp import CAPPClient

class HedgingAgent:
    def __init__(self, client: CAPPClient, local_currency: str):
        self.client = client
        self.local_currency = local_currency

    async def poll_erp_system(self):
        """Mock pulling NetSuite / Xero for future-dated USD liabilities"""
        print("Checking ERP for new D+30 USD liabilities...")
        due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        return [
            {"invoice_id": "INV-789", "amount_usd": 25000.0, "due_date": due_date, "vendor": "AWS"}
        ]

    async def execute_hedge(self, liability: dict):
        print(f"\n[HEDGE TRIGGERED] {liability['amount_usd']} USD due on {liability['due_date']} for {liability['vendor']}.")
        print("Locking in FX rate today...")

        try:
            # We instantly swap local currency to stablecoins and hold it in the internal wallet
            res = await self.client.payments.send(
                amount=liability["amount_usd"],
                from_currency=self.local_currency,
                to_currency="USDC",
                recipient="self_treasury",
                corridor=f"{self.local_currency[:2]}-US" # simple mock corridor string
            )
            print(f"Hedge Execution TX: {res.tx_id}")
            print("Funds are now safely pegged to USD and parked. FX risk eliminated.")
            
        except Exception as e:
            print(f"Hedge failed to execute: {e}")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        # e.g., a Nigerian corporation earning NGN but spending USD
        agent = HedgingAgent(client=client, local_currency="NGN")
        
        liabilities = await agent.poll_erp_system()
        for liability in liabilities:
            await agent.execute_hedge(liability)

if __name__ == "__main__":
    asyncio.run(main())
