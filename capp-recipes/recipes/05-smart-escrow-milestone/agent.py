import asyncio
import os
from capp import CAPPClient

class EscrowAgent:
    def __init__(self, client: CAPPClient, freelancer_wallet: str, corridor: str):
        self.client = client
        self.freelancer_wallet = freelancer_wallet
        self.corridor = corridor
        self.total_budget_usd = 5000.0
        self.amount_released_usd = 0.0

    async def poll_github_milestones(self):
        """Mock pulling PR statuses or milestone events."""
        print("Polling project management events...")
        return [
            {"id": "milestone-1", "title": "Frontend Setup", "status": "approved", "payout_pct": 20},
            {"id": "milestone-2", "title": "Backend API", "status": "approved", "payout_pct": 40},
            {"id": "milestone-3", "title": "Integration", "status": "pending", "payout_pct": 40}
        ]

    async def execute_payout(self, milestone: dict):
        if milestone["status"] != "approved":
            print(f"Milestone {milestone['title']} is not approved. Skipping.")
            return

        payout_amount = self.total_budget_usd * (milestone["payout_pct"] / 100)
        
        print(f"\n[Escrow Trigger] '{milestone['title']}' approved.")
        print(f"Releasing {payout_amount} USD to freelancer...")

        try:
            res = await self.client.payments.send(
                amount=payout_amount,
                from_currency="USD",
                to_currency="NGN", # Or target local currency
                recipient=self.freelancer_wallet,
                corridor=self.corridor
            )
            self.amount_released_usd += payout_amount
            print(f"Success! TX: {res.tx_id}. Total released so far: {self.amount_released_usd} USD")
        except Exception as e:
            print(f"Escrow release failed: {e}")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        agent = EscrowAgent(client, freelancer_wallet="0xabc987", corridor="US-NG")
        
        milestones = await agent.poll_github_milestones()
        for m in milestones:
            await agent.execute_payout(m)

if __name__ == "__main__":
    asyncio.run(main())
