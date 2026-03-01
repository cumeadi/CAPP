# Recipe 06: Dollar-Cost Averaging (DCA) Agent

## Business Problem
In high-inflation markets, users lose purchasing power if they wait until the end of the month to convert local fiat into stable assets. Manual conversion is tedious.

## How It Works
This agent implements automated micro-investing:
1. **Monitors Bank API**: Polls a user's local mobile money or open-banking API for their daily balance.
2. **Sweeps**: Calculates a fixed percentage (or fixed amount) of the balance to sweep.
3. **Converts & Parks**: Uses CAPP to swap the swept local currency (e.g., NGN or KES) into a high-yield stablecoin (like cUSD) on a low-fee chain (like Polygon or Aptos).

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/06-dollar-cost-averaging
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Integrate with Plaid or Mono (for African open banking) to read real bank balances.
- Trigger the sweep instantly via Webhook only when a new deposit hits the user's account, instead of polling daily.
