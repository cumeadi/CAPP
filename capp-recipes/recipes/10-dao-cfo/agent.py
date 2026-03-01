import asyncio
import os
from capp import CAPPClient, CAPPApprovalRequired

class DAOCFOAgent:
    def __init__(self, client: CAPPClient):
        self.client = client

    async def poll_snapshot_proposals(self):
        """Mock pulling approved governance proposals"""
        print("Checking Snapshot for newly passed funding proposals...")
        return [
            {
                "proposal_id": "0x4a9b...7f1c",
                "title": "Fund Nairobi Dev Guild",
                "status": "passed",
                "grant_amount_usd": 5000.0,
                "grantee_wallet": "0xGuildWallet",
                "target_currency": "KES",
                "corridor": "US-KE"
            }
        ]

    async def draft_and_propose_transaction(self, proposal: dict):
        print(f"\n[GOVERNANCE TRIGGER] Proposal Passed: '{proposal['title']}'")
        print(f"Drafting {proposal['grant_amount_usd']} USD cross-border payout to {proposal['grantee_wallet']} in {proposal['target_currency']}...")

        try:
            # We attempt to send it. Because the DAO API Key would have strict policies
            # (e.g. limit=0 USD for immediate send), this will trigger an Approval exception.
            await self.client.payments.send(
                amount=proposal["grant_amount_usd"],
                from_currency="USDC", # Assuming DAO holds stablecoins
                to_currency=proposal["target_currency"],
                recipient=proposal["grantee_wallet"],
                corridor=proposal["corridor"]
            )
            print("Transaction executed directly! (Wait, policies should have prevented this...)")
            
        except CAPPApprovalRequired as e:
            # This is the expected flow for a DAO
            print(f"Draft successfully submitted to Multi-Sig Approval queue!")
            print(f"CAPP Approval ID generated: {e.approval_id}")
            print("Message to DAO Signers: Please log into the CAPP Portal to sign and execute this payload.")
            
        except Exception as e:
            print(f"Failed to draft transaction: {e}")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        agent = DAOCFOAgent(client=client)
        
        proposals = await agent.poll_snapshot_proposals()
        for prop in proposals:
            await agent.draft_and_propose_transaction(prop)

if __name__ == "__main__":
    asyncio.run(main())
