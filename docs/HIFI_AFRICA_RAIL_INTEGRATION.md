# HIFI Africa Rail Integration

## Overview

CAPP now supports **local currency pay-ins and pay-outs across Africa** via HIFI's Africa Rail — a unified payment rail that handles both **bank transfers** and **mobile money** (M-PESA, MTN, Airtel) through a single API. This integration enables users to deposit local currency into their CAPP treasury and withdraw to local bank accounts or mobile wallets across 15 African countries.

The integration is deployed in **beta mode** with conservative defaults, feature flags, circuit breakers, and automatic fallback to existing MMO providers.

---

## What Was Done

### 1. Data Model Changes

**`applications/capp/capp/models/payments.py`**
- Added `TransactionDirection` enum (`PAYIN`, `PAYOUT`) to distinguish deposit vs withdrawal flows
- Added `RailProvider` enum (`HIFI_AFRICA`, `MPESA`, `MTN`, `AIRTEL`, `ORANGE`, `SWIFT`, `ACH`)
- Added `HifiIdType` enum (`DRIVERS`, `ID_CARD`, `PASSPORT`, `RESIDENCE_PERMIT`)
- Extended `SenderInfo` and `RecipientInfo` with structured KYC fields: `first_name`, `last_name`, `date_of_birth`, `address_line1/2`, `state_province_region`, `postal_code`, `additional_id_type`, `additional_id_number` (Nigeria-specific)
- Added `direction`, `rail_provider`, `provider_transaction_id` to `CrossBorderPayment` and `PaymentRoute`
- Added `BusinessInfo` model for KYB (business verification)

**`applications/capp/capp/core/database.py`**
- Added `direction`, `rail_provider`, `provider_transaction_id` columns to the `Payment` table
- Created `HifiKYCSubmission` table for tracking individual/business KYC submissions to HIFI

**`applications/capp/capp/utils/payment_mapper.py`**
- Added bidirectional mapping for the new fields between Pydantic and SQLAlchemy models

### 2. HIFI Integration Package (New)

**`packages/integrations/hifi/`** — Complete integration package:

| File | Purpose |
|------|---------|
| `config.py` | `HifiConfig` — API credentials, beta flags, transaction limits, allowed countries |
| `country_config.py` | Corridor definitions for 15 countries, payment method capabilities, Nigeria-specific requirements |
| `models.py` | HIFI API request/response models, KYC/KYB payloads, field mapper (`map_sender_to_hifi_kyc`) |
| `client.py` | Async HTTP client with retry logic, exponential backoff, authentication |
| `adapter.py` | `HifiAfricaRailAdapter(BasePaymentRail)` — main adapter implementing `quote_transfer`, `execute_transfer`, `verify_status`, plus KYC/KYB submission and directed transfers |
| `exceptions.py` | `HifiIntegrationException`, `HifiKYCException`, `HifiCorridorNotSupportedException`, `HifiBetaLimitExceededException` |

### 3. Configuration & Feature Flags

**`applications/capp/capp/config/settings.py`** — 8 new settings:

| Setting | Default | Purpose |
|---------|---------|---------|
| `HIFI_API_KEY` | `""` | API authentication |
| `HIFI_API_SECRET` | `""` | API authentication |
| `HIFI_BASE_URL` | `https://sandbox.hifi.africa/v1` | API endpoint |
| `HIFI_ENABLED` | `false` | Master on/off switch |
| `HIFI_BETA_MODE` | `true` | Enables conservative limits |
| `HIFI_MAX_TRANSACTION_AMOUNT` | `1000.0` | Beta transaction cap |
| `HIFI_ALLOWED_COUNTRIES` | `[]` (empty = all) | Explicit country allow-list |
| `HIFI_FALLBACK_ENABLED` | `true` | Fallback to existing providers on failure |

**`env.example`** — Updated with all HIFI environment variables.

### 4. Backend Orchestration Wiring

**`applications/capp/capp/services/payment_orchestration.py`**
- `_initialize_hifi()` — Conditionally creates adapter and circuit breaker when `HIFI_ENABLED=true`
- `_should_use_hifi()` — Decides whether to route via HIFI based on feature flags, circuit breaker state, country support, and explicit provider selection
- `_execute_hifi_payment()` — Full execution flow: KYC validation → field mapping → directed transfer → circuit breaker tracking → fallback on failure
- Modified `_execute_mmo_payment()` to check HIFI as a candidate before using existing MMO providers

**`applications/capp/capp/services/mmo_availability.py`**
- Added `get_rail_providers_by_country()` — Returns both HIFI and existing MMO providers for route optimization

**`applications/capp/capp/services/compliance.py`**
- Added 11 HIFI corridor countries to country regulations
- Added `validate_hifi_kyc_completeness()` — Validates all required HIFI KYC fields, including Nigeria-specific additional ID enforcement

### 5. Wallet API Endpoints (New)

**`applications/capp/capp/api/v1/endpoints/wallet.py`** — 3 new endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wallet/hifi/corridors` | GET | List available HIFI corridors (filtered by allowed countries) |
| `/wallet/hifi/deposit` | POST | Initiate a local currency pay-in via bank transfer or mobile money |
| `/wallet/hifi/withdraw` | POST | Initiate a local currency pay-out to bank account or mobile wallet |

- Updated `GET /wallet/stats` to include `hifi` object with `enabled`, `corridor_count`, and `beta` status

All endpoints include: corridor validation, beta limit checks, Nigeria additional ID enforcement, structured error responses.

### 6. Frontend Updates

**`apps/web/services/api.ts`**
- Added TypeScript types: `HifiCorridor`, `HifiDepositRequest`, `HifiWithdrawRequest`, `HifiTransactionResponse`
- Added API methods: `getHifiCorridors()`, `hifiDeposit()`, `hifiWithdraw()`

**`apps/web/components/DepositModal.tsx`**
- Added **Crypto / Local Currency** tab switcher
- Local Currency tab: Country selector → Deposit form with Mobile Money / Bank Transfer toggle, amount input, KYC fields (name, email, phone), Nigeria additional ID fields, processing state, success confirmation with transaction ID

**`apps/web/components/WithdrawModal.tsx`**
- Added **Crypto / Local Currency** tab switcher
- Local Currency tab: Country selector → Withdraw form with payment method toggle, recipient details, bank account/code fields (for bank transfers), mobile money number (for mobile money), Nigeria additional ID, success confirmation

**`apps/web/components/TreasuryCard.tsx`**
- Added **Africa Rail** card to the asset allocation grid with Beta badge, showing corridor count
- Grid expanded from 4 to 5 columns

---

## What We Have Now

### Supported Countries (15 corridors)

**Full Pay-in + Pay-out (10):**
| Country | Currency | Notes |
|---------|----------|-------|
| Benin (BJ) | XOF | |
| Botswana (BW) | BWP | |
| Cameroon (CM) | XAF | |
| Cote d'Ivoire (CI) | XOF | |
| Malawi (MW) | MWK | |
| Nigeria (NG) | NGN | Requires additional ID (BVN/NIN), no KYB |
| Tanzania (TZ) | TZS | |
| Togo (TG) | XOF | |
| Uganda (UG) | UGX | |
| Zambia (ZM) | ZMW | |

**Pay-out Only (5):**
| Country | Currency |
|---------|----------|
| Burkina Faso (BF) | XOF |
| Kenya (KE) | KES |
| Mali (ML) | XOF |
| Senegal (SN) | XOF |
| South Africa (ZA) | ZAR |

### Payment Methods
- **Mobile Money**: Instant to 1 business day
- **Bank Transfer**: 1-3 business days

### Beta Safety Layers
1. **Feature flag** (`HIFI_ENABLED`) — Master switch, off by default
2. **Beta mode** (`HIFI_BETA_MODE`) — Conservative transaction limits
3. **Country allow-list** (`HIFI_ALLOWED_COUNTRIES`) — Explicit opt-in per country
4. **Circuit breaker** — Opens after 3 failures in 5 minutes, auto-recovers
5. **Automatic fallback** — On HIFI failure, retries via existing MMO/bank providers

---

## Impact

### For Users
- Can now deposit local currency (bank transfer or mobile money) directly into their CAPP treasury
- Can withdraw from treasury to local bank accounts or mobile wallets
- Seamless tab-based UX: existing crypto flows untouched, local currency is an additional option

### For the Platform
- Expands CAPP's reach to 15 African markets with local currency on/off ramps
- Unified rail replaces the need for individual MMO integrations in supported countries
- Route optimizer can now consider HIFI alongside existing providers for optimal routing
- KYC compliance validated before every transaction

### For Operations
- Zero-risk rollout: everything is behind feature flags, off by default
- Gradual country-by-country enablement via `HIFI_ALLOWED_COUNTRIES`
- Circuit breaker prevents cascading failures
- All transactions logged with `rail_provider` and `provider_transaction_id` for tracing

---

## How to Enable

1. Set environment variables in `.env`:
   ```env
   HIFI_API_KEY=your-api-key
   HIFI_API_SECRET=your-api-secret
   HIFI_BASE_URL=https://sandbox.hifi.africa/v1
   HIFI_ENABLED=true
   HIFI_BETA_MODE=true
   HIFI_MAX_TRANSACTION_AMOUNT=1000.0
   HIFI_ALLOWED_COUNTRIES=NG,KE,TZ,UG,ZA
   HIFI_FALLBACK_ENABLED=true
   ```

2. Run the database migration (pending creation — see Recommended Next Steps)

3. Restart the backend server

---

## Files Changed Summary

| File | Action |
|------|--------|
| `applications/capp/capp/models/payments.py` | Modified — enums, KYC fields, direction |
| `applications/capp/capp/core/database.py` | Modified — Payment columns, HifiKYCSubmission table |
| `applications/capp/capp/utils/payment_mapper.py` | Modified — new field mappings |
| `applications/capp/capp/config/settings.py` | Modified — 8 HIFI settings |
| `applications/capp/capp/services/payment_orchestration.py` | Modified — HIFI routing, execution, fallback |
| `applications/capp/capp/services/mmo_availability.py` | Modified — HIFI in provider lookup |
| `applications/capp/capp/services/compliance.py` | Modified — HIFI KYC validation, country regulations |
| `applications/capp/capp/api/v1/endpoints/wallet.py` | Modified — 3 new endpoints, updated stats |
| `apps/web/services/api.ts` | Modified — HIFI types and API methods |
| `apps/web/components/DepositModal.tsx` | Modified — Local Currency tab |
| `apps/web/components/WithdrawModal.tsx` | Modified — Local Currency tab |
| `apps/web/components/TreasuryCard.tsx` | Modified — Africa Rail card |
| `packages/integrations/hifi/` (7 files) | Created — Full integration package |
| `env.example` | Modified — HIFI env vars |

---

## Recommended Next Steps

### High Priority
1. **Alembic Migration** — Create the database migration for the new `payments` columns and `hifi_kyc_submissions` table. The SQLAlchemy models are defined but the migration script hasn't been generated yet.

2. **Sandbox Integration Testing** — Test against HIFI's sandbox API with real API credentials. The adapter is built but needs end-to-end validation against the actual HIFI endpoints.

3. **KYC Persistence** — Wire the `HifiKYCSubmission` table into the deposit/withdraw endpoints so KYC data is stored and reused across transactions (currently KYC is submitted per-transaction).

4. **Webhook Receiver** — Implement a webhook endpoint for HIFI to send async status updates (transaction completed, failed, KYC approved/rejected). Currently we rely on polling via `verify_status()`.

### Medium Priority
5. **Transaction History** — Add a UI component showing HIFI transaction history with status tracking (pending → processing → completed/failed).

6. **Exchange Rate Display** — Show real-time exchange rates (local currency ↔ USD/USDC) in the deposit/withdraw forms before the user confirms.

7. **KYC Pre-fill** — Auto-populate KYC fields from the user's profile so returning users don't re-enter information.

8. **HIFI Adapter Registration in `main.py`** — Move adapter initialization from `PaymentOrchestrationService` to the FastAPI startup hook for centralized lifecycle management.

### Lower Priority
9. **GA Readiness Dashboard** — Track HIFI success rates, latency, and error types to evaluate when to exit beta (remove the 0.8x reliability penalty, raise transaction limits).

10. **KYB (Business) Flow** — Build the business verification UI for non-Nigeria countries. The backend `submit_business_kyb()` is implemented but there's no frontend form yet.

11. **Recipient Saved Accounts** — Let users save frequently-used bank accounts and mobile money numbers for faster withdrawals.

12. **Multi-Currency Quoting** — Use HIFI's `quote_transfer` to show fees and estimated delivery before execution, rather than executing directly.
