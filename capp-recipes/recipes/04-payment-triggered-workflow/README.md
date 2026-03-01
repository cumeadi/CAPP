# Recipe 04: Payment-Triggered Workflow Agent

## Business Problem
CAPP's real power for product builders is as a payment middleware layer—not just executing payments, but wiring payment settlement into broader business workflows. This recipe demonstrates the meta-pattern: payment settles, agent fires a webhook (or action) to a downstream system.

## How It Works
1. **Subscribes** to global `payment.settled` events via CAPP's SSE endpoints.
2. **Routes** the event to a specific downstream workflow handler based on corridor or memo data.
3. **Executes** the downstream action (e.g., releasing a digital product, triggering a fulfillment API).

## Examples Included
- **E-commerce**: payment settled → release digital download link
- **Supply chain**: payment settled → trigger warehouse fulfillment API
- **SaaS**: payment settled → activate subscription in billing system
- **Marketplace**: payment settled → update escrow state, notify buyer and seller

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/04-payment-triggered-workflow
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Use AWS EventBridge or Kafka to publish CAPP events to your entire microservice fleet.
- Store idempotent keys so workflows aren't triggered multiple times if the stream restarts.
