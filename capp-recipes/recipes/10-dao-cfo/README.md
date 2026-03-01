# Recipe 10: DAO "CFO" Agent

## Business Problem
DAOs and web3 communities struggle to manage real-world expenses. If a community approves a grant that requires payout in NGN, KES, and USD, it requires massive manual coordination by multi-sig signers to bridge, swap, and route funds correctly.

## How It Works
This agent acts as an autonomous CFO for the DAO:
1. **Listens to Governance**: It monitors a DAO voting portal (like Snapshot or Discourse) for approved spending proposals.
2. **Drafts Payload**: Once a proposal passes, it drafts the complex cross-border payment payload.
3. **Requests Approval**: Instead of executing directly (since it lacks full treasury control), it pushes the transaction into the CAPP `approvals` module.
4. **Execution**: The human multi-sig signers review the CAPP approval request. Once signed, CAPP handles all the asset swaps and cross-border routing instantly.

## Prerequisites
- `capp-sdk`
- `CAPP_API_KEY` set in environment

## Quickstart
```bash
cd recipes/10-dao-cfo
pip install -r requirements.txt
python agent.py
```

## Extending This Recipe
- Integrate the Snapshot API to trigger actions automatically when a proposal hits the "Closed/Passed" state.
- Wire the CAPP `status` endpoint to post a transaction receipt back in the DAO's Discord channel when the multi-sig signers finally approve the execution.
