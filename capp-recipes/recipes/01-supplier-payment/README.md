# Recipe 01: Cross-Border Supplier Payment Agent

## Business Problem
Every import/export business operating across African borders faces the same friction: invoice approved on Monday, payment arrives Thursday, supplier frustrated by Tuesday. CAPP eliminates that gap. This recipe demonstrates an agent that watches an invoice approval queue and executes payment the moment approval is granted—sub-2-second settlement, optimal routing, full compliance trail.

## How It Works
1. **Polls** an invoice queue (e.g., a CSV, DB, or webhook).
2. **Validates** the recipient against a supplier allowlist.
3. **Analyzes Routes** and executes payment via the optimal corridor.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/01-supplier-payment
pip install -r requirements.txt
python agent.py
```

## Configuration
- `CORRIDOR`: Default `NG-KE`
- `POLL_INTERVAL_SEC`: Default `30`
- `APPROVAL_THRESHOLD_USD`: Default `5000`
- `SUPPLIER_ALLOWLIST`: Target known safety wallets
- `MAX_FEE_PCT`: Default `1.5`

## Extending This Recipe
- Connect the `poll_invoice_queue` method to an actual SQL database.
- Wire `request_human_approval` to Slack or Teams API.
- Add dynamic FX rate limits via the `/routing/fx` endpoints in CAPP.
