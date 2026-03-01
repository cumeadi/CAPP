# Recipe 09: Automated Hedging Agent

## Business Problem
Corporate treasuries in highly inflationary environments suffer from severe FX risk. If an invoice or tax liability is due in 30 days in USD, but revenues are earned in local currency, the liability inflates every day.

## How It Works
This agent acts as an autonomous corporate treasurer taking delta-neutral positions:
1. **Invoice Logged**: It monitors the ERP system (like NetSuite or Xero) for upcoming D+30 payables formatted in hard currency.
2. **Immediate Hedge**: The moment the liability is known, the agent uses CAPP to instantly convert the required local fiat into a USD stablecoin, parking it natively.
3. **Maturity Payment**: On day 30, it pulls the parked stablecoin funds and executes the final B2B international wire/crypto transfer via CAPP.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/09-automated-hedging
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Fetch open invoices actively from the Xero Accounting API or Quickbooks Online API.
- Use the CAPP Yield Module to earn interest on the stablecoins while they are parked for 30 days awaiting the invoice due date.
