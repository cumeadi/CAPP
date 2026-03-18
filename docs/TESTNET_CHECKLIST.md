# CAPP Testnet Testing Checklist

This checklist provides systematic test scenarios to verify CAPP functionality across all testnet chains.

**⏱️ Estimated Testing Time: 30-60 minutes**

---

## Pre-Testing Setup

Before running tests, complete these prerequisites:

- [ ] Backend running on http://127.0.0.1:8000
- [ ] Frontend running on http://localhost:3000
- [ ] `.env` or environment variables loaded with `ALCHEMY_API_KEY=FX7-uiaeRx_TaEyI2HGC0`
- [ ] At least one testnet wallet funded (see TESTNET_SETUP.md for faucets)
- [ ] Petra wallet extension installed (for Aptos testing)

---

## Phase 1: Connectivity & RPC Verification

### 1.1 Backend RPC Health Check

**Objective**: Verify all backend RPC endpoints are responding

```bash
# Test Aptos RPC
curl -s http://127.0.0.1:8000/wallet/stats | jq '.'

# Expected response:
# {
#   "total_value_usd": <number>,
#   "hot_wallet_balance": <number>,
#   "yield_balance": <number>,
#   "apy": <number>,
#   "is_sweeping": <boolean>,
#   ...
# }
```

**Test Cases:**
- [ ] Response HTTP 200 OK
- [ ] `total_value_usd` is a number
- [ ] `apy` is a number between 0-20
- [ ] No error messages in response

### 1.2 Frontend RPC Connection Check

**Objective**: Verify Web3Provider loads testnet chains

**Steps:**
1. Open http://localhost:3000 in browser
2. Open browser DevTools (F12)
3. Click "CONNECT EVM" button
4. Check that you see these testnet chains:

**Test Cases:**
- [ ] Ethereum Sepolia appears in chain list
- [ ] Polygon Amoy appears in chain list
- [ ] Base Sepolia appears in chain list
- [ ] Arbitrum Sepolia appears in chain list
- [ ] Optimism Sepolia appears in chain list

---

## Phase 2: Wallet Connection Testing

### 2.1 EVM Wallet Connection (RainbowKit)

**Objective**: Test EVM wallet connection via RainbowKit/Wagmi

**Steps:**
1. Click "CONNECT EVM" button
2. Select a wallet (MetaMask, Coinbase, WalletConnect, etc.)
3. Approve connection in wallet popup
4. Verify connection succeeds

**Test Cases:**
- [ ] Wallet selector appears after clicking "CONNECT EVM"
- [ ] Wallet popup triggers without error
- [ ] Connection is confirmed in CAPP UI
- [ ] Connected wallet address displays in the header
- [ ] Can disconnect without error (click address → Disconnect)

**Repeat for at least 2 different wallets:**
- [ ] Wallet 1: __________ (name)
- [ ] Wallet 2: __________ (name)

### 2.2 Aptos Wallet Connection

**Objective**: Test Aptos wallet connection via Petra

**Prerequisites:**
- Petra wallet installed: https://petra.app/
- Petra switched to testnet mode

**Steps:**
1. Click "LINK APTOS" button
2. Select Petra from wallet list
3. Approve connection in Petra popup
4. Verify connection succeeds

**Test Cases:**
- [ ] "LINK APTOS" button is visible
- [ ] Petra appears in available wallets list
- [ ] Petra popup opens without error
- [ ] Connection is confirmed in CAPP UI
- [ ] Aptos account address displays (format: 0x...)
- [ ] Can disconnect without error (click address or "Unplug" icon)

---

## Phase 3: Balance Fetching & Display

### 3.1 EVM Chain Balances

**Objective**: Verify balance fetching from each EVM testnet chain

**Test Cases for Each Chain (Sepolia, Polygon Amoy, Base Sepolia, Arbitrum Sepolia):**

| Chain | Connected? | Balance Displayed? | Correct Format? | USD Value Shown? |
|-------|------------|--------------------|-----------------|------------------|
| Ethereum Sepolia | [ ] | [ ] | [ ] | [ ] |
| Polygon Amoy | [ ] | [ ] | [ ] | [ ] |
| Base Sepolia | [ ] | [ ] | [ ] | [ ] |
| Arbitrum Sepolia | [ ] | [ ] | [ ] | [ ] |

**Expected Format Examples:**
- ETH: `0.5234 ETH` (4 decimals)
- MATIC: `10.5 MATIC`
- USDC: `1234 USDC`

### 3.2 Aptos Balance

**Objective**: Verify Aptos APT balance fetching

**Steps:**
1. Connect Aptos wallet (see Phase 2.2)
2. Observe "YOUR ASSETS" section in dashboard
3. Look for APT asset card

**Test Cases:**
- [ ] APT asset card appears in "YOUR ASSETS"
- [ ] Balance shows as number (e.g., `1.5234 APT`)
- [ ] USD value calculated correctly (balance × $10)
- [ ] APT balance matches Petra wallet display
- [ ] No error messages in browser console

### 3.3 Backend Balance Endpoint

**Objective**: Verify backend `/wallet/stats` returns testnet balances

```bash
# Test endpoint
curl -s http://127.0.0.1:8000/wallet/stats | jq '.'

# Expected format:
# {
#   "total_value_usd": 1234.56,
#   "hot_wallet_balance": 500.00,
#   "yield_balance": 234.56,
#   "aptos_balance": 1.5,
#   "solana_balance": 15000.5,
#   "stellar_balance": 50000.0,
#   "apy": 6.8,
#   "is_sweeping": true
# }
```

**Test Cases:**
- [ ] HTTP 200 response
- [ ] All numeric fields are numbers (not strings)
- [ ] `aptos_balance` ≥ 0
- [ ] `solana_balance` and `stellar_balance` return mock values (expected behavior)
- [ ] `apy` is between 0-20

---

## Phase 4: Payment Routing Engine

### 4.1 Routing Calculation

**Objective**: Test the routing engine with testnet payments

**API Endpoint:** `POST http://127.0.0.1:8000/routing/calculate`

**Test Payload:**
```json
{
  "amount": 100,
  "currency": "USDC",
  "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f56bEd",
  "preference": "CHEAPEST"
}
```

**Test Cases:**

1. **Cost-Optimized Route:**
   ```bash
   curl -X POST http://127.0.0.1:8000/routing/calculate \
     -H "Content-Type: application/json" \
     -d '{
       "amount": 100,
       "currency": "USDC",
       "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f56bEd",
       "preference": "CHEAPEST"
     }' | jq '.'
   ```
   - [ ] Returns HTTP 200
   - [ ] `recommended_route.fee_usd` is lower than other routes
   - [ ] `recommended_route.eta_seconds` indicates longer time
   - [ ] `recommendation_score` is between 0-1

2. **Speed-Optimized Route:**
   ```bash
   curl -X POST http://127.0.0.1:8000/routing/calculate \
     -H "Content-Type: application/json" \
     -d '{
       "amount": 100,
       "currency": "USDC",
       "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f56bEd",
       "preference": "FASTEST"
     }' | jq '.'
   ```
   - [ ] Returns HTTP 200
   - [ ] `recommended_route.eta_seconds` is lowest among routes
   - [ ] `recommended_route.fee_usd` may be higher
   - [ ] Routes sorted by recommendation score

3. **Different Amounts:**
   - [ ] Test with amount: 1 USDC → Returns valid routes
   - [ ] Test with amount: 10000 USDC → Returns valid routes
   - [ ] Test with amount: 0.01 USDC → Returns valid routes

---

## Phase 5: Yield Optimization

### 5.1 Smart Sweep Status

**Objective**: Verify yield optimization features are working

**API Endpoint:** `GET http://127.0.0.1:8000/wallet/stats`

```bash
curl -s http://127.0.0.1:8000/wallet/stats | jq '.is_sweeping'
```

**Test Cases:**
- [ ] Response includes `is_sweeping` boolean
- [ ] If `is_sweeping: true`, dashboard shows "SMART SWEEP ACTIVE (X.X% APY)"
- [ ] If `is_sweeping: false`, no sweep indicator shown

### 5.2 Yield Balance Tracking

**Objective**: Verify yield balance calculation

**Steps:**
1. Note current `yield_balance` from `/wallet/stats`
2. Trigger yield optimization (if available)
3. Verify yield balance updates

**Test Cases:**
- [ ] `yield_balance` is a non-negative number
- [ ] `hot_wallet_balance` + `yield_balance` = `total_value_usd` (approximately)
- [ ] `apy` is between 0-20% (reasonable for DeFi)
- [ ] Balances update without error

---

## Phase 6: Cross-Chain Scenarios

### 6.1 Multi-Chain Balance View

**Objective**: Verify the dashboard correctly aggregates balances across multiple chains

**Scenario:**
1. Connect EVM wallet with balance on 2+ chains
2. Connect Aptos wallet
3. View "YOUR ASSETS" section

**Test Cases:**
- [ ] Total Portfolio Value sums all assets correctly
- [ ] Each chain's balance card displays correct amount
- [ ] Mock prices are applied correctly:
  - ETH: $2000/unit
  - APT: $10/unit
  - USDC: $1/unit
  - SOL: $150/unit (mock)
  - XLM: $0.12/unit (mock)
- [ ] Portfolio value updates without reloading page

### 6.2 Sequential Chain Testing

Test the same user flow on each testnet:

| Testnet | Wallet Connected | Balance Fetched | Total Value Calculated | Status |
|---------|------------------|-----------------|------------------------|--------|
| Sepolia | [ ] | [ ] | [ ] | ✅ ❌ |
| Polygon Amoy | [ ] | [ ] | [ ] | ✅ ❌ |
| Base Sepolia | [ ] | [ ] | [ ] | ✅ ❌ |
| Arbitrum Sepolia | [ ] | [ ] | [ ] | ✅ ❌ |
| Aptos Testnet | [ ] | [ ] | [ ] | ✅ ❌ |

---

## Phase 7: Error Handling

### 7.1 Network Errors

**Objective**: Verify graceful error handling

**Test Cases:**

1. **Disconnect RPC:**
   - [ ] Stop backend API
   - [ ] Frontend still loads without crashing
   - [ ] Balance shows $0.00 (fallback)
   - [ ] Error logged in console (not blocking)

2. **Invalid Wallet Address:**
   ```bash
   curl -X POST http://127.0.0.1:8000/routing/calculate \
     -H "Content-Type: application/json" \
     -d '{
       "amount": 100,
       "currency": "USDC",
       "recipient": "invalid_address",
       "preference": "CHEAPEST"
     }'
   ```
   - [ ] Returns HTTP 400 or 422 (validation error)
   - [ ] Error message is descriptive

3. **Wallet Rejection:**
   - [ ] User rejects wallet connection popup
   - [ ] Frontend handles rejection gracefully
   - [ ] No unhandled promise rejection errors
   - [ ] "CONNECT EVM" button still clickable

---

## Phase 8: Performance & UX

### 8.1 Load Times

**Objective**: Verify reasonable performance

**Measurements:**
- [ ] Frontend loads at http://localhost:3000 in < 3 seconds
- [ ] Balance fetch completes in < 2 seconds after wallet connection
- [ ] Routing calculation completes in < 2 seconds
- [ ] No visible lag when switching between chains

### 8.2 Responsiveness

**Objective**: Verify UI is responsive across devices

**Test Cases:**
- [ ] Desktop (1920×1080) - All elements visible and clickable
- [ ] Tablet (768×1024) - Content reflows correctly
- [ ] Mobile (375×812) - All functionality accessible

---

## Phase 9: Documentation & Support

### 9.1 Setup Guide Accuracy

- [ ] TESTNET_SETUP.md steps are clear and accurate
- [ ] All provided faucet links are working
- [ ] Alchemy API key works without issues
- [ ] Environment variable instructions are correct

### 9.2 Error Messages

- [ ] All error messages are user-friendly
- [ ] Console errors include helpful context
- [ ] No cryptic error codes without explanation

---

## Summary

### Checklist Completion

**Total Tests:** _____ / _____
**Passed:** _____ ✅
**Failed:** _____ ❌
**Skipped:** _____ ⏭️

**Overall Status:**
- [ ] All tests passed ✅
- [ ] Most tests passed (> 80%)
- [ ] Many tests failed (< 80%)
- [ ] Critical failures blocking testnet use

### Known Issues / Failures

```
Issue 1: _________________________________
Affected Phase: ___
Severity: Critical / High / Medium / Low
Notes: ________________________________

Issue 2: _________________________________
Affected Phase: ___
Severity: Critical / High / Medium / Low
Notes: ________________________________
```

### Recommendations for Next Steps

1. ___________________________________
2. ___________________________________
3. ___________________________________

---

## Appendix: Useful Commands

```bash
# Check backend status
curl -s http://127.0.0.1:8000/health

# Get all wallet stats
curl -s http://127.0.0.1:8000/wallet/stats | jq '.'

# Calculate route for payment
curl -X POST http://127.0.0.1:8000/routing/calculate \
  -H "Content-Type: application/json" \
  -d '{"amount":100,"currency":"USDC","recipient":"0x...","preference":"CHEAPEST"}' | jq '.'

# Monitor backend logs
tail -f backend.log

# Monitor frontend (if running with npm run dev)
# Check browser console with F12

# Restart backend
lsof -ti:8000 | xargs kill -9
python3 -m uvicorn apps.api.app.main:app --reload --port 8000

# Restart frontend
# Press Ctrl+C in terminal, then: npm run dev
```

---

**Testing completed on:** ________________
**Tested by:** ________________
**Comments:** ________________________________________________________________

