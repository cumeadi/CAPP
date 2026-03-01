---
sidebar_position: 1
---

# Quickstart

Get a working CAPP integration making cross-border payments in under 10 minutes.

## 1. Get an API Key

1. Sign up at the [CAPP Developer Portal](https://sandbox.canza.io)
2. Retrieve your sandbox API key (starts with `sk_test_`).

## 2. Install the SDK

The CAPP SDK is available for both Python and TypeScript.

### Python (Async First)
```bash
pip install capp-sdk
```

### TypeScript
```bash
npm install @canza/capp-sdk
```

## 3. Check Sandbox Balances

Your sandbox API key comes with pre-funded wallets on the Aptos, Polygon, and Starknet testnets.

### Python
```python
import asyncio
from capp import CAPPClient

async def check_balance():
    async with CAPPClient(api_key="sk_test_your_key", sandbox=True) as client:
        balances = await client.wallet.get_balance()
        print("Aptos balance:", balances.aptos)
        print("Polygon balance:", balances.polygon)

asyncio.run(check_balance())
```

### TypeScript
```typescript
import { CAPPClient } from '@canza/capp-sdk';

async function checkBalance() {
    const client = new CAPPClient({ apiKey: 'sk_test_your_key', sandbox: true });
    const balances = await client.wallet.getBalance();
    console.log('Aptos balance:', balances.aptos);
    console.log('Polygon balance:', balances.polygon);
}
checkBalance();
```

## 4. Send Your First Payment

Let's send 100 USD from NGN to KES across the Nigeria-Kenya corridor.

### Python
```python
async def send_payment():
    async with CAPPClient(api_key="sk_test_your_key", sandbox=True) as client:
        result = await client.payments.send(
            amount=100.0,
            from_currency="NGN",
            to_currency="KES",
            recipient="0xabc...123",
            corridor="NG-KE"
        )
        print("Transaction ID:", result.tx_id)
```

### TypeScript
```typescript
async function sendPayment() {
    const client = new CAPPClient({ apiKey: 'sk_test_your_key', sandbox: true });
    const result = await client.payments.send({
        amount: 100.0,
        fromCurrency: "NGN",
        toCurrency: "KES",
        recipient: "0xabc...123",
        corridor: "NG-KE"
    });
    console.log("Transaction ID:", result.txId);
}
```

## 5. Explore Agent Recipes

Now that you've run a payment, explore our production-ready [Agent Recipes](https://github.com/canza-foundation/capp-recipes) to see how you can automate treasury rebalancing, mass payroll, and payment-triggered workflows using AI agents and the CAPP protocol.
