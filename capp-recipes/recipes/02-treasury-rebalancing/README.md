# Recipe 02: Treasury Rebalancing Agent

## Business Problem
Businesses holding multi-currency positions across African corridors constantly drift from target allocations as payments flow and FX rates move. Manually rebalancing is slow, expensive, and nobody's full-time job. This agent monitors wallet balances, detects drift beyond configurable thresholds, and rebalances automatically.

## How It Works
1. **Monitors Balances** across all configured chains and currencies via CAPP.
2. **Calculates Drift** between actual portfolio value and the target allocation.
3. **Executes Rebalance** using the optimal CAPP corridors when drift exceeds the allowed threshold.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/02-treasury-rebalancing
pip install -r requirements.txt
python agent.py
```

## Configuration
- `DRIFT_THRESHOLD`: The percentage of drift allowed before triggering a rebalance (e.g. 0.05 for 5%).
- `TARGET_ALLOCATION`: A JSON string defining target token allocations.

## Extending This Recipe
- Store historical portfolio snapshots in a database for analytics.
- Integrate with Smart Sweep API (yielding) for idle assets during the rebalance interval.
- Tie the rebalancing schedule to a cron job or Celery task.
