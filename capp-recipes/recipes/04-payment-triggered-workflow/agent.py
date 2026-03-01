import asyncio
import os
from capp import CAPPClient, CorridorEvent

# Workflow Definitions
async def release_digital_product(event: CorridorEvent):
    tx_id = event.data.get("tx_id", "Unknown")
    amount = event.data.get("amount", 0)
    print(f"[E-Commerce] Payment {tx_id} settled for {amount}. Releasing product download link...")

async def trigger_fulfillment_api(event: CorridorEvent):
    tx_id = event.data.get("tx_id", "Unknown")
    amount = event.data.get("amount", 0)
    print(f"[Supply Chain] Payment {tx_id} settled for {amount}. Pushing order to warehouse API...")

async def activate_subscription(event: CorridorEvent):
    tx_id = event.data.get("tx_id", "Unknown")
    user_id = event.data.get("user_id", "User123")
    print(f"[SaaS] Payment {tx_id} settled. Activating subscription for user {user_id}...")

async def marketplace_escrow_update(event: CorridorEvent):
    tx_id = event.data.get("tx_id", "Unknown")
    print(f"[Marketplace] Payment {tx_id} settled. Releasing escrow to seller wallet...")

class PaymentWorkflowAgent:
    def __init__(self, client: CAPPClient, workflows: dict):
        self.client = client
        self.workflows = workflows

    async def run(self):
        print("Starting workflow agent. Listening for settlement events...")
        try:
            async for event in self.client.corridors.subscribe_all():
                if event.type == "payment.settled":
                    workflow = self.workflows.get(event.corridor)
                    if workflow:
                        await workflow(event)
                    else:
                        print(f"No workflow mapped for corridor: {event.corridor}")
        except asyncio.CancelledError:
            print("Shutting down workflow agent.")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    # Map payment corridors (or mock event conditions) to downstream actions
    workflows = {
        "NG-KE": release_digital_product,
        "GH-NG": trigger_fulfillment_api,
        "ZA-NG": activate_subscription,
        "US-KE": marketplace_escrow_update
    }
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        agent = PaymentWorkflowAgent(client, workflows)
        
        # Since we are mocking an infinite SSE stream in the real world, 
        # for recipe demonstration we'll simulate an artificial event stream 
        # by manually calling the handler instead of waiting forever.
        print("--- Simulation Mode ---")
        mock_event_1 = CorridorEvent(type="payment.settled", corridor="NG-KE", data={"tx_id": "tx_abc", "amount": 50})
        mock_event_2 = CorridorEvent(type="payment.settled", corridor="GH-NG", data={"tx_id": "tx_def", "amount": 1200})
        mock_event_3 = CorridorEvent(type="payment.settled", corridor="ZA-NG", data={"tx_id": "tx_ghi", "user_id": "Cus_89"})
        mock_event_4 = CorridorEvent(type="payment.settled", corridor="US-KE", data={"tx_id": "tx_jkl"})
        
        for e in [mock_event_1, mock_event_2, mock_event_3, mock_event_4]:
            wf = agent.workflows.get(e.corridor)
            if wf:
                await wf(e)
                await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
