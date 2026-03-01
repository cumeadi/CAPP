import asyncio
import os
from capp import CAPPClient, CAPPApprovalRequired

class SupplierPaymentAgent:
    def __init__(self, client: CAPPClient, corridor: str):
        self.client = client
        self.corridor = corridor
        self.allowlist = os.getenv("SUPPLIER_ALLOWLIST", "").split(",")
        self.max_fee_pct = float(os.getenv("MAX_FEE_PCT", "1.5"))

    async def poll_invoice_queue(self):
        """Mock invoice queue polling."""
        print("Polling invoice queue...")
        return [
            {
                "id": "INV-001",
                "amount_usd": 1500,
                "from_currency": "NGN",
                "to_currency": "KES",
                "supplier_wallet": "0xabc123"
            }
        ]

    async def process_invoice(self, invoice: dict):
        print(f"Processing invoice {invoice['id']} for {invoice['amount_usd']} USD")
        
        # 1. Analyze routes before committing
        routes = await self.client.routing.analyze(
            amount=invoice["amount_usd"],
            from_currency=invoice["from_currency"],
            to_currency=invoice["to_currency"],
            corridor=self.corridor
        )
        
        if not routes:
            print("No viable routes found.")
            return

        best_route = routes[0]
        if (best_route.fee_usd / invoice["amount_usd"]) * 100 > self.max_fee_pct:
            print("Fee exceeds maximum percentage limit.")
            return

        # 2. Execute on best route
        try:
            result = await self.client.payments.send(
                amount=invoice["amount_usd"],
                from_currency=invoice["from_currency"],
                to_currency=invoice["to_currency"],
                recipient=invoice["supplier_wallet"],
                corridor=self.corridor
            )
            print(f"Payment successful: {result.tx_id}")
            return result
        # 3. Handle approval threshold gracefully
        except CAPPApprovalRequired as e:
            await self.request_human_approval(invoice, e.approval_id)

    async def request_human_approval(self, invoice, approval_id):
        print(f"ACTION REQUIRED: Human approval needed for {invoice['id']}")
        print(f"Approval ID: {approval_id}")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    corridor = os.getenv("CORRIDOR", "NG-KE")
    
    # Initialize in sandbox mode
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        agent = SupplierPaymentAgent(client=client, corridor=corridor)
        
        # Run exactly once for demonstration
        invoices = await agent.poll_invoice_queue()
        for idx in invoices:
            await agent.process_invoice(idx)

if __name__ == "__main__":
    asyncio.run(main())
