# Recipe 08: Subscription Churn Rescue Agent

## Business Problem
International SaaS adoption in emerging markets is heavily bottlenecked by FX banking limits and frequent credit card declines. When a Nigerian or Kenyan user's primary card fails on Stripe, the subscription churns permanently.

## How It Works
1. **Intercepts Webhook**: The agent listens for `invoice.payment_failed` from a billing provider (like Stripe).
2. **Generates Local Link**: It automatically determines the user's localized currency pricing and generates a CAPP payment request.
3. **Rescues**: It emails or SMS messages the user a link ("Pay 4,000 NGN directly via Mobile Money/Bank Transfer to restore access").
4. **Settles & Activates**: When the user fulfills the CAPP request, CAPP settles the USD to the SaaS provider, and the agent pings the billing provider to reactivate the user.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/08-subscription-churn-rescue
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Actually plug this into Stripe's webhook engine natively using FastAPI.
- Use Twilio SDK to text the localized payment instructions directly to the churning user via SMS.
