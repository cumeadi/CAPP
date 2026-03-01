# Recipe 05: Smart Escrow & Milestone Agent

## Business Problem
Freelancers across Africa often face massive delays and extortionate fees when getting paid by international clients. Traditional escrow services take high cuts and settle slowly. 

## How It Works
This agent acts as a programmable, trustless escrow. 
1. **Funded**: It monitors an on-chain smart contract (or internal CAPP balance) for the total project budget.
2. **Listens**: It hooks into standard project management tools. In this recipe, we simulate a GitHub webhook or Jira status change.
3. **Releases**: When a pull request is merged or a milestone is marked "Complete," the agent uses CAPP to release a fractional milestone payment, converted instantly and routed to the freelancer's local currency wallet.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/05-smart-escrow-milestone
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Integrate with the official GitHub Webhooks API using FastAPI.
- Wire up the `approvals` module in CAPP so a human client must still click "Approve" upon PR merge before funds fly.
- Handle dispute resolution by allowing the agent to route funds to an arbitration multi-sig if a deadline is missed.
