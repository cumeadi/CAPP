# Recipe 07: FX Arbitrage & Liquidity Agent

## Business Problem
FX rates and liquidity pool depths fluctuate widely across different African corridors. When local pairs drift out of sync, the network needs liquidity providers to step in and restore market equilibrium.

## How It Works
This is a high-frequency sub-agent acting as an automated market maker/arbitrageur:
1. **Polls FX Rates**: Constantly watches the CAPP `/routing` and `/corridors` endpoints.
2. **Calculates Circular Value**: It looks for spread gaps. Example: `NGN -> KES -> cUSD -> NGN`. If the circular trace yields > 1.0 (after fees), an arbitrage gap exists.
3. **Executes**: Immediately fires CAPP payments to route its own funds through the circular path, capturing the spread.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/07-fx-arbitrage
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Implement real-time websockets using the CAPP `subscribe_all` endpoint to react to `liquidity.updated` events instead of polling APIs.
- Bind the agent to an external borrowing protocol (like Aave) to utilize flash loans, vastly increasing the arbitrage size without needing heavy capital on hand.
