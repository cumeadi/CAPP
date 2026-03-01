---
sidebar_position: 2
---

# API Reference

The CAPP API operates over HTTP JSON and strongly-typed SDKs. Below are the core objects and methods.

## Authentication
Every request must include the `Authorization: Bearer <API_KEY>` header. Agent requests must additionally pass the `X-Agent-Credential: <TOKEN>` header for policy verification.

## Payments (`/payments`)

### `POST /v1/payments/send`
Executes a cross-border payment over the CAPP network.

**Payload:**
```json
{
  "amount": 1000.0,
  "from_currency": "NGN",
  "to_currency": "KES",
  "recipient": "0xabc...",
  "corridor": "NG-KE"
}
```

### `GET /v1/payments/{tx_id}`
Retrieves the status of a specific payment.

## Routing (`/routing`)

### `POST /v1/routing/analyze`
Simulates a transaction and analyzes the available liquidity pools, returning optimal chains, expected fees, and settlement ETAs.

## Wallet (`/wallet`)

### `GET /v1/wallet/balances`
Returns the total balance across all connected wallets and chains, or optionally filterable by `chain` or `currency`.

## Agents (`/agents`)

### `POST /v1/agents/credentials`
Issues an autonomous credential token bound to a specific policy.

**Payload:**
```json
{
  "corridor_allowlist": ["NG-KE", "GH-NG"],
  "max_per_tx_usd": 2000.0,
  "daily_limit_usd": 10000.0,
  "require_approval_above_usd": 5000.0,
  "expiry_days": 30
}
```

## Corridors (`/corridors`)

### `GET /v1/corridors/{corridor}/events`
SSE Stream emitting liquidity and health events in real-time.

---

## Sandbox Mode (`/sandbox`)
The CAPP Sandbox Environment operates using the `sk_test_...` API keys and simulates execution and routing without moving real funding.

### `POST /v1/sandbox/inject-failure`
Triggers an artificial failure for testing exception handling.

### `POST /v1/sandbox/reset`
Restores all default sandbox state and mock balances.
