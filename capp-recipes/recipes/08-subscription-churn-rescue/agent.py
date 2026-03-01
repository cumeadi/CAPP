import asyncio
import os
from capp import CAPPClient

class ChurnRescueAgent:
    def __init__(self, client: CAPPClient, base_subscription_usd: float):
        self.client = client
        self.base_subscription_usd = base_subscription_usd

    async def handle_stripe_webhook_failure(self):
        """Mocks receiving an invoice.payment_failed event from Stripe"""
        print("Webhook received: invoice.payment_failed")
        return {
            "user_id": "usr_999",
            "email": "ayo.dev@example.ng",
            "country": "NG",
            "currency_preference": "NGN"
        }

    async def generate_rescue_link(self, user_data: dict):
        print(f"Calculating localized pricing for {user_data['country']}...")
        
        # Route analysis to find how much NGN it takes to settle the USD base
        routes = await self.client.routing.analyze(
            amount=self.base_subscription_usd,
            from_currency=user_data["currency_preference"],
            to_currency="USD",
            corridor=f"{user_data['country']}-US"
        )
        
        if not routes:
            print("No viable routes found to rescue this subscription.")
            return

        best_route = routes[0]
        local_cost = best_route.estimated_input_amount
        
        # In reality, you'd generate a Paystack/Flutterwave or CAPP Checkout link
        payment_link = f"https://pay.canza.io/rescue?u={user_data['user_id']}&amt={local_cost}&cur={user_data['currency_preference']}"
        
        print(f"\n[EMAIL DISPATCH] To: {user_data['email']}")
        print(f"Subject: Action Required - Payment Failed")
        print(f"Body: Your card was declined. Don't lose access! Pay {local_cost:,.2f} {user_data['currency_preference']} locally here:")
        print(f"Link: {payment_link}\n")

async def main():
    api_key = os.getenv("CAPP_API_KEY", "sk_REDACTED")
    
    async with CAPPClient(api_key=api_key, sandbox=True) as client:
        # SaaS product costs $29 USD/month
        agent = ChurnRescueAgent(client=client, base_subscription_usd=29.0)
        
        failed_user = await agent.handle_stripe_webhook_failure()
        await agent.generate_rescue_link(failed_user)

if __name__ == "__main__":
    asyncio.run(main())
