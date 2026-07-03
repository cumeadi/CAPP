# CAPP — Technical Walkthrough

This document is for engineers. It walks through the system architecture, the payment lifecycle, how each agent works, and what the current gaps are. It also proposes a concrete efficiency roadmap and institutional value-adds.

---

## Architecture

CAPP is a monorepo with two FastAPI applications that share an agent/service layer.

```
capp/
├── apps/
│   └── api/                        # App A — demo/legacy stack
│       └── app/
│           ├── main.py             # Entry point, mounts all routers
│           ├── routers/            # 17 router modules, prefix-based
│           ├── schemas.py          # Pydantic request/response models
│           └── services/           # Lightweight service wrappers
│
├── applications/
│   └── capp/capp/                  # App B — production stack
│       ├── main.py                 # Entry point, security middleware stack
│       ├── api/v1/                 # Versioned routes under /api/v1
│       ├── agents/                 # 7 autonomous agents
│       ├── services/               # Full service layer (30+ modules)
│       ├── models/                 # Domain models (payments.py is authoritative)
│       ├── core/                   # Chain clients, auth, middleware, circuit breaker
│       └── adapters/               # Yield and rail adapters
│
├── packages/
│   ├── core/                       # Multi-agent orchestration + consensus engine
│   ├── intelligence/               # LLM providers, compliance agent, market analyst
│   ├── ml/                         # RL training env + PPO route scorer
│   ├── integrations/               # HIFI, mobile money, banking, blockchain clients
│   ├── capp-sdk/                   # Python API client
│   └── capp-sdk-ts/                # TypeScript API client
│
├── sdk/                            # High-level FinancialFramework SDK
├── capp-recipes/                   # 10 runnable agent examples
└── apps/developer-portal/          # Docusaurus docs site
```

### The two-app split

**App A** (`apps/api/`) is the demo and sandbox stack. It uses simpler API-key auth, has direct chain operation routes (Starknet account deployment, Plasma bridge), and runs the `ChainListenerService` and `WebhookDispatcherService` as background tasks. Routes are unprefixed (e.g. `/wallet/send`).

**App B** (`applications/capp/capp/`) is the production stack. It adds JWT auth (`/api/v1/auth`), `SecurityHeadersMiddleware`, `RequestValidationMiddleware`, `AgentAuthMiddleware`, and a `validate_all_secrets_on_startup()` check. All routes are under `/api/v1`.

Both apps import from the same `applications/capp/capp/agents/` and `applications/capp/capp/services/` — the agent and service layer is shared. The domain models in `applications/capp/capp/models/payments.py` are authoritative; App A's `apps/api/app/schemas.py` is a parallel representation of the same domain (a known tech debt point — see Roadmap).

### SDK layers

Three levels of abstraction for different integration depths:

1. **Direct API client** (`packages/capp-sdk` / `packages/capp-sdk-ts`) — thin async HTTP wrappers around the CAPP REST API. Modules: `payments`, `routing`, `wallet`, `corridors`, `agents`, `approvals`, `events`, `compliance`, `yield_api`. Use this when you want to call the API from your own app.

2. **Orchestration framework** (`packages/core`) — multi-agent coordination engine. Contains `PaymentOrchestrator`, `AgentCoordinator`, `TaskManager`, `ConsensusEngine`, `PerformanceTracker`. Use this when you're building custom agents that need to coordinate decisions.

3. **High-level framework** (`sdk/canza_agents/`) — `FinancialFramework` class configured with `Region`, `ComplianceLevel`, `RiskTolerance` enums. Wraps the orchestration layer with sensible defaults for African payment corridors. Use this for getting something running fast.

---

## Payment Lifecycle

Every payment moves through this state machine:

```
PENDING
  └─► ROUTING          (Route Optimization Agent scoring corridors)
        └─► PROCESSING  (Compliance Agent screening)
              ├─► COMPLIANCE_REVIEW   (manual hold — high risk score)
              └─► SETTLING            (Settlement Agent submitting tx)
                    ├─► YIELD_UNWINDING   (DeFi Agent withdrawing from Aave)
                    └─► COMPLETED
FAILED / CANCELLED / EXPIRED
OFFLINE_QUEUED   (no connectivity — queued for sync)
```

The `CrossBorderPayment` model (`models/payments.py`) carries the full audit trail: agent_id, principal_id, initiated_by ("human" or "agent"), workflow_id, blockchain_tx_hash, compliance_status, fraud_score, risk_level, rail_provider, provider_transaction_id.

`YIELD_UNWINDING` is a state unique to CAPP: when the DeFi Agent has deployed settlement funds to Aave and a payment arrives, the agent must withdraw first. The payment status pauses here while that happens, then resumes to SETTLING.

`OFFLINE_QUEUED` is baked into the model with `offline_queued: bool`, `sync_attempts: int`, and `last_sync_attempt: datetime`. No separate queue — the payment itself carries this state.

### Payment orchestration flow

`PaymentOrchestrationService` (`services/payment_orchestration.py`) runs this sequence:

1. **Exchange rate fetch** — `ExchangeRateService` aggregates from 4 source types (central bank, commercial bank, forex market, mobile money) with weighted average.
2. **Route optimization** — `RouteOptimizationAgent` evaluates up to 50 candidate routes.
3. **Compliance check** — `ComplianceAgent` runs KYC/AML/sanctions in parallel (max 20 concurrent checks, 30s timeout each).
4. **Liquidity reservation** — `LiquidityAgent` reserves funds in the target pool (5-min expiry, auto-release on failure).
5. **Settlement** — `SettlementAgent` batches the payment (1–10 per batch, up to 60s wait) and submits to the selected chain.
6. **Metrics collection** — `MetricsCollector` records latency, success rate, fees at each stage.

---

## Agent System

All agents inherit from `BasePaymentAgent` (`agents/base.py`), which provides structured logging via structlog, lifecycle management (start/stop), and registration in `agent_registry`. Each agent has a typed `AgentConfig` subclass.

### Route Optimization Agent
**File:** `agents/routing/route_optimization_agent.py`

Evaluates candidate routes using a multi-objective scoring function:
- Cost weight: 0.4
- Speed weight: 0.3
- Reliability weight: 0.2
- Compliance weight: 0.1

Scores are normalized by `sklearn.preprocessing.MinMaxScaler`, then the trained RL model (`RLRouteScorer`) overrides the final selection. Results are Redis-cached for 5 minutes (TTL configurable). Multi-hop routing (up to 2 hops) is supported but disabled by default.

### Settlement Agent
**File:** `agents/settlement/settlement_agent.py`

Manages a payment queue and batches payments every 10 seconds (or when batch reaches 10 items). Submits to the chain selected during routing. Has service handles for Aptos, Polygon, Solana (mock), and Stellar (mock). Retries up to 3 times with 5-minute delay between attempts. Requires finality confirmation before marking COMPLETED.

### Compliance Agent
**File:** `agents/compliance/compliance_agent.py`

Runs up to 5 check types in parallel:
- **KYC** — triggered at $1,000+
- **AML** — triggered at $3,000+
- **Enhanced due diligence** — triggered at $10,000+
- **Sanctions** — always runs; SDN fuzzy match via `thefuzz` with configurable score threshold
- **PEP + adverse media** — always runs when enabled

Uses `AIComplianceAgent` (`packages/intelligence/compliance/agent.py`) for LLM-backed reasoning over the sanctions context. Returns an `overall_risk_score` (0–1) and a list of `violations`. Feeds result to `FraudDetectionService` for velocity and structuring checks. 7-year retention, configurable.

### Liquidity Management Agent
**File:** `agents/liquidity/liquidity_agent.py`

Manages `LiquidityPool` objects per currency pair. Reserves funds for in-flight payments (5-minute expiry). Triggers rebalancing when any pool drifts 20% from target allocation. Uses `AIAdaptiveStrategy` (`agents/liquidity/strategies.py`) backed by `MarketAnalysisAgent` for rebalancing decisions.

### Yield (DeFi) Agent
**File:** `agents/defi/yield_agent.py`

Runs a monitoring loop every 10 minutes. For each configured `YieldStrategy`:
1. Checks liquid balance on target chain (Arbitrum, Base)
2. If balance > `min_idle_amount` (default $1,000 USDC), deposits excess to Aave V3 via `ExecutorService`
3. When a payment requires more liquidity than is liquid, withdraws just-in-time

This is the mechanism behind `YIELD_UNWINDING` payment status. Yearn Finance is also supported via adapter (`adapters/yearn.py`).

### Relayer Agent
**File:** `agents/relayer/agent.py`

Executes cross-chain routes. Monitors Starknet bridge for `TokensLocked` events every 10 seconds and triggers `release_funds` on Aptos when a lock is detected. For payments with `route_details` in metadata, delegates to `RelayerService` which selects the appropriate bridge adapter (MockBridge in sandbox, real bridge adapters in production).

### Exchange Rate Agent
**File:** `agents/exchange/exchange_rate_agent.py`

Aggregates rates from 4 source types with configurable weights:
- Central bank: 0.4
- Commercial bank: 0.3
- Forex market: 0.2
- Mobile money: 0.1

Locks rates for 5 minutes with a 0.1% buffer (`rate_lock_buffer_percentage`). Detects arbitrage opportunities above 0.5% spread (`arbitrage_threshold_percentage`), max $10,000 per arbitrage action. Refreshes every 60 seconds. Up to 10 concurrent source requests.

---

## Consensus Engine

**Files:** `packages/core/consensus/`

`mechanisms.py` is the single canonical `ConsensusEngine`. The former placeholder in `consensus_engine.py` has been replaced by a re-export shim. Both callers are wired to the real implementation and all 14 unit tests pass (`tests/unit/test_consensus_engine.py`).

**`reach_consensus(results, threshold=None)`** is polymorphic:
- Called with `List[ProcessingResult]` (orchestrator path) → returns `ProcessingResult` via the configured majority/weighted/unanimous/threshold/median/average mechanism.
- Called with `List[AgentResult]` and an optional `threshold` override (SDK framework path) → returns `AgentConsensusResult` with `consensus_reached`, `recommended_action`, and `agent_recommendations`.

**`initialize()`** is an async no-op that satisfies the framework lifecycle protocol.

**`ConsensusConfig`** is optional — `ConsensusEngine()` defaults to 70% majority consensus with a 30-second timeout and a minimum of 2 agents.

Supported voting strategies (`voting.py`, also tested):

| Strategy | Intended use |
|---|---|
| SIMPLE_MAJORITY | Standard route selection |
| WEIGHTED_MAJORITY | When agents have different reliability scores |
| UNANIMOUS | High-value or high-risk transactions |
| SUPER_MAJORITY | Configurable threshold (default 0.67) |
| RANKED_CHOICE | Multi-option decisions (route selection from >2 candidates) |
| APPROVAL | Each agent approves/rejects independently |

`Vote`, `VotingSession`, and `VotingResult` models (agent_id, vote_value, confidence, timeout, min/max votes, agent_weights) live in `voting.py` and are exercised end-to-end by the unit tests.

---

## RL-Based Route Scoring

**Files:** `packages/ml/`

The Route Optimization Agent uses a PPO model trained with `stable_baselines3`.

**Observation space** (per-route feature vector, up to 5 routes):
```
[amount_normalized, fee_pct, time_normalized, reliability, compliance_score, is_valid]
```
Total observation dimension: `(5 routes × 5 features) + 1 context feature = 26`

**Action space:** Discrete — select one of N routes (N ≤ 5)

**Training environment:** `PaymentRoutingEnv` (Gymnasium-compatible, `packages/ml/environments/payment_routing_env.py`)

**Fallback:** If the model file is missing or can't load, `RLRouteScorer.select_best_route_index()` returns index 0 (first candidate). The multi-objective score from `RouteOptimizationAgent` still runs — the RL model overrides the final selection, not the scoring.

**Gap:** No CI/CD pipeline for retraining. The training script (`packages/ml/training/train_agent.py`) exists but isn't wired to a GitHub Actions workflow. See Roadmap.

---

## LLM Intelligence Layer

**Files:** `packages/intelligence/`

Three LLM-backed agents, all using an `LLMProvider` interface with a Gemini implementation and a `MockLLMProvider` fallback (used when `GEMINI_API_KEY` is unset).

### AIComplianceAgent
Receives the transaction details + simulated sanctions context, runs `TRANSACTION_SCREENING_PROMPT` through the LLM, and returns a structured compliance verdict with human-readable reasoning. Designed to handle name variations that rule-based fuzzy matching might miss.

### MarketAnalysisAgent
Analyzes on-chain metrics (`ChainMetricsService`) + real-time market data (`RealTimeMarketService`) to recommend optimal settlement timing. Has its own `AgentWallet` with a $100/day budget and uses `X402Client` to autonomously pay for premium data feeds when standard sources are insufficient (see x402 section).

### LiquidityAgent (intelligence layer)
Uses `VOLATILITY_ANALYSIS_PROMPT` to assess corridor liquidity risk and recommend rebalancing amounts. Called by the Liquidity Management Agent when the standard threshold logic is insufficient.

---

## x402: Agents Paying for Data

**Files:** `core/x402_client.py`, `core/agent_wallet.py`

`X402Client` wraps `aiohttp` and handles HTTP 402 Payment Required responses automatically:
1. Makes initial GET request
2. If 402 is returned, parses `WWW-Authenticate: X402` headers for `amount`, `currency`, and `address`
3. Pays via `AgentWallet.send()` (deducted from daily budget)
4. Retries the original request

`AgentWallet` maintains a daily spend budget (`BudgetManager`) that resets at midnight. Before any spend, it calls `can_spend(amount)` against the remaining daily budget. If the budget is exhausted, the request fails cleanly rather than silently degrading.

This means agents can autonomously upgrade their data quality mid-operation — e.g. the Market Analyst pays for a premium CoinMarketCap endpoint when the free tier is rate-limited — without any human intervention.

---

## Chain and Rail Selection

A `PaymentRoute` carries three parallel routing dimensions:

| Field | What it selects |
|---|---|
| `from_chain` / `to_chain` | Which blockchain networks are used |
| `bridge_provider` | Which cross-chain bridge (Stargate, Across, Hop, CCTP, Hyperlane, LayerZero, Li.Fi) |
| `rail_provider` | Which payment rail (HIFI_AFRICA, MPESA, MTN, AIRTEL, ORANGE, SWIFT, ACH) |

These can combine: a payment might use HIFI Africa Rail for the fiat leg and Polygon as the settlement chain. The Route Optimization Agent scores routes across all combinations and selects the best one before settlement begins. (A consensus/voting confirmation step is available via the Consensus Engine — see that section.)

The `PaymentRouter` (`core/router.py`) directly queries each chain's live gas/fee state (Aptos via `AptosSettlementService`, Polygon via `PolygonSettlementService`, Starknet via Alchemy RPC) before scoring. No stale estimates.

---

## Agent Credential System

**Files:** `models/agent_credential.py`, `api/v1/endpoints/agents.py`, `core/agent_auth_middleware.py`

This is the institutional access control primitive. Every autonomous system (a cron job, a trading bot, an internal treasury tool) gets its own credential with explicit policy constraints.

**Credential structure:**
```
organization_id  (which org owns this)
principal_id     (which human is accountable)
parent_agent_id  (if delegated — creates a tree)

max_per_tx_usd          (hard cap per transaction)
daily_limit_usd         (rolling 24h spend cap)
require_approval_above_usd  (human-in-the-loop threshold)
corridor_allowlist      (e.g. ["NG-KE", "GH-NG"])
chain_allowlist         (e.g. [APTOS, POLYGON])
allowed_tools           (MCP tool names this agent can invoke)
expiry_days             (credential TTL, 1–365 days)
```

**Enforcement** (`AgentAuthMiddleware`):
1. Intercepts requests with `X-API-Key: capp_agent_*` header
2. Looks up credential, verifies bcrypt hash
3. Checks `is_active`
4. Validates daily spend against `daily_limit_usd`
5. Checks corridor and chain allowlists against the request payload
6. Injects `agent_credential` and `agent_id` into request state

**Delegation** (`POST /api/v1/agents/credentials/{parent_agent_id}/delegate`):
- Max depth: 2 (agent → sub-agent, no further)
- Permissions can only narrow: a sub-credential cannot have higher limits or broader allowlists than its parent
- A parent can revoke all sub-credentials by deactivating itself

---

## Autonomy Controls

**Design spec:** `design_specs/command_and_control_ux.md`

CAPP defines four autonomy levels, surfaced as `autonomy_level` in `AgentConfig`:

| Level | Name | Behavior |
|---|---|---|
| 0 | PAUSED | Agent takes no actions, queues all decisions for review |
| 1 | COPILOT | Every action requires explicit human approval before execution |
| 2 | GUARDED | Acts autonomously below `require_approval_above_usd`; pauses above it |
| 3 | SOVEREIGN | Fully autonomous within credential policy limits |

The "Signing Ceremony" is the design pattern for changing autonomy level: it requires an explicit signed approval request (`SignedApprovalRequest` schema, carrying a cryptographic signature) — not just a config update. This prevents accidental privilege escalation.

At GUARDED and SOVEREIGN levels, agents can still be interrupted via `POST /agents/reject/{request_id}` with a signed rejection.

---

## Offline Support

`CrossBorderPayment` carries offline state natively:
- `offline_queued: bool` — set when network is unavailable at submission time
- `sync_attempts: int` — incremented on each retry
- `last_sync_attempt: datetime` — timestamp of most recent retry

There is no separate offline queue table — payments in `OFFLINE_QUEUED` status sit in the main payments table. A sync loop checks for these periodically and retries. The `allow_offline_processing: bool` preference in `PaymentPreferences` lets senders opt in or out.

---

## Running a Recipe: Payroll Distribution

This walkthrough shows how `capp-recipes/recipes/03-payroll-distribution/agent.py` works end to end. It's a real example of CAPP in use.

**The problem:** A company with employees across Nigeria, Kenya, and Ghana needs to run payroll without managing multiple bank accounts, FX conversions, and per-country settlement times manually.

**The agent:**

```python
async with CAPPClient(api_key=api_key, sandbox=True) as client:
    agent = PayrollAgent(client)

    # 1. Load payroll CSV
    records = agent.load_payroll_csv("payroll.csv")

    # 2. Preflight: check total balance covers payroll
    await agent.preflight_check(records)

    # 3. Group by corridor for routing efficiency
    grouped = agent.group_by_corridor(records)

    # 4. Execute each corridor batch in sequence
    for corridor, batch in grouped.items():
        results = await agent.execute_batch(batch)

    # 5. Output reconciliation CSV
    agent.generate_report(all_results, "payroll_summary.csv")
```

**What happens inside `execute_batch`:** For each employee, `client.payments.send()` triggers the full CAPP payment lifecycle — route optimization, compliance, settlement — and returns a `tx_id`. The agent records success/failure per employee. Failed payments are retried at the corridor batch level.

**Input CSV:**
```
employee_id,name,wallet_address,amount_usd,target_currency,corridor
EMP001,Amara Okafor,0xabc...,2400,NGN,NG-KE
EMP002,David Kimani,0xdef...,1800,KES,NG-KE
EMP003,Ama Asante,0xghi...,2100,GHS,GH-NG
```

**Extensions available out of the box (per the recipe README):**
- Pull from Workday or local HRIS via API instead of CSV
- Push payslips to employees via email with transaction receipts
- Auto-reconcile into NetSuite or Xero via ERP API

**Run it in sandbox:**
```bash
cd capp-recipes/recipes/03-payroll-distribution
pip install -r requirements.txt
CAPP_API_KEY=sk_sandbox_... python agent.py
```

---

## Efficiency Roadmap

These are the highest-impact engineering improvements, roughly ordered by effort vs. value.

### 1. Merge the two apps into one versioned API
**Impact:** Eliminates duplicate CORS configs, duplicate auth systems, duplicate wallet/compliance routes, and the App A schema duplication.
**Approach:** App B (`/api/v1`) absorbs App A's unique routes (Starknet ops, Plasma bridge, sandbox, admin DLQ, anomalies) under `/api/v1` or `/api/v0` for transition. Single `main.py` entry point. `apps/api/app/schemas.py` is deleted; callers updated to import from `models/payments.py`.

### 2. Batch payment endpoint
**Impact:** Unblocks institutional buyers immediately. `PaymentBatch` model and `bulk_disbursement` `PaymentType` are both already defined.
**Approach:** Add `POST /api/v1/payments/batch` backed by `PaymentOrchestrationService`. The orchestration loop already handles lists — the endpoint just needs to validate the batch, persist a `PaymentBatch` record, and fan out to the per-payment orchestration flow.

### 3. Analytics endpoint
**Impact:** `PaymentAnalytics` model is fully defined with all the fields you'd want (volume, count, success rate, fees, delivery time, currency/country/MMO distribution).
**Approach:** Add `GET /api/v1/analytics/summary?period=monthly&start=...&end=...` backed by an async SQLAlchemy aggregation query against the payments table.

### 4. Persist BillingService
**Impact:** Billing accounts and API keys survive restarts.
**Approach:** Add a `developer_accounts` table using the existing async SQLAlchemy session pattern. `BillingService` becomes a repository on top of it. Pattern is already established in `repositories/user.py` and `repositories/payment.py`.

### 5. Extend rate lock window
**Impact:** Institutional treasury buyers need 24h+ rate certainty for hedging.
**Approach:** Make `rate_lock_duration_minutes` a per-credential field (default 5, max 1440). `ExchangeRateAgent` reads it from the request credential context.

### 6. RL model retraining pipeline
**Impact:** Model improves with real payment outcome data instead of staying frozen at training time.
**Approach:** Add a GitHub Actions workflow triggered weekly (or on N new completed payments). Training script (`packages/ml/training/train_agent.py`) already exists. Output model artifact versioned in S3 or GCS; `RLRouteScorer` loads by version.

### 7. Consistent circuit breaker wiring
**Impact:** `CircuitBreaker` is defined and works, but it's not obvious it's applied to all external service calls.
**Approach:** Wrap every call to HIFI adapter, MMO providers, chain RPCs, and DefiLlama in `CircuitBreaker.execute()`. A decorator pattern on service methods would make this low-friction.

### 8. Reconciliation API
**Impact:** Core banking integration hook. Institutions need to reconcile CAPP payments against their internal GL.
**Approach:** Expose `GET /api/v1/admin/reconciliation/run` (triggers `ReconciliationService.run()`) and `GET /api/v1/admin/reconciliation/status` (returns last run result). Push drift alerts as webhook events.

---

## Institutional Value-Add Roadmap

Capabilities institutions will pay for, roughly ordered by proximity to what's already built.

### 1. Bulk Disbursement API (`POST /api/v1/payments/batch`)
Model exists. Build the endpoint. See Roadmap #2 above.

### 2. Treasury Dashboard API
Multi-chain balance aggregation + yield positions + P&L in one API call. `WalletStats` + `YieldService.get_yield_balance()` already return the pieces. Combine them into a `GET /api/v1/treasury/dashboard` response.

### 3. KYB (Business Verification)
`BusinessInfo` model (`models/payments.py`) is defined with `business_name`, `tax_identification_number`, `country`. Build the onboarding endpoint and wire it to the Compliance Agent's EDD flow. HIFI Africa Rail supports KYB for all countries except Nigeria.

### 4. Compliance Report Push
Institutions need compliance reports delivered to their systems on schedule — not pulled manually. Add a webhook subscription type for `compliance.report.ready` that posts a signed pre-signed S3 URL or SFTP path to the institution's configured endpoint.

### 5. SLA-Backed Corridors
Route scoring already carries `success_rate`, `reliability_score`, and `estimated_delivery_time`. Expose SLA tiers as a route preference:
- `STANDARD`: best effort, ≤ 24h
- `EXPRESS`: ≥ 97% reliability, ≤ 15 min
- `INSTANT`: blockchain settlement only, ~seconds

Map each tier to route selection weight overrides. Institutions pay a premium for EXPRESS/INSTANT.

### 6. Sub-Account Architecture
`organization_id` + `principal_id` + agent credential delegation tree already models this. Surface it explicitly as a multi-tenant API: one institution (org), N departments (sub-accounts, each with own credential), isolated spend limits and audit trails. Add `GET /api/v1/organizations/{org_id}/accounts` and per-account analytics.

### 7. FX Forward Contracts
Extend the `RateLock` model in `ExchangeRateAgent` to support multi-day locks with forward rate quotes. Add `POST /api/v1/fx/forward` that books a rate for a future settlement date. Backs hedging and pre-funding use cases.

### 8. Reconciliation API (push mode)
Beyond the pull API (Roadmap #8), add a push mode: when the reconciliation watchdog detects a ledger vs. on-chain drift above 0.01%, post a signed webhook to the institution's configured endpoint. Core banking risk teams need real-time drift alerts, not scheduled reports.

---

## Known Production Gaps

Be explicit with prospects about these:

| Gap | Status | Notes |
|---|---|---|
| Solana integration | Sandbox mock | `SolanaBridgeClient` returns mock balances. Not usable for real settlement. |
| Stellar integration | Sandbox mock | Same pattern as Solana. |
| Billing persistence | In-memory | `BillingService` loses all state on restart. |
| RL model retraining | Manual | Training script exists; no CI/CD yet. |
| Batch payment endpoint | Missing | Model defined; route not built. |
| Analytics endpoint | Missing | Model defined; route not built. |
| Rate lock window | Fixed at 5 min | Too short for institutional FX hedging. |
| Two-app split | Active debt | Overlapping routes, schemas, auth systems. |

---

## Environment Variables Reference

Key variables that change runtime behavior:

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | Set to `production` to enforce `SECRET_KEY` validation |
| `GEMINI_API_KEY` | unset | LLM features fall back to `MockLLMProvider` if unset |
| `CHAOS_ENABLED` | `false` | Enable `ChaosMonkey` for resilience testing |
| `CHAOS_FAILURE_RATE` | `0.5` | Fraction of requests that fail when chaos is enabled |
| `HIFI_ENABLED` | `false` | Gate HIFI Africa Rail routes |
| `HIFI_BETA_MODE` | `true` | Enforces `HIFI_MAX_TRANSACTION_AMOUNT` cap |
| `FRAUD_DETECTION_ENABLED` | `true` | Toggle velocity + structuring checks |
| `FRAUD_THRESHOLD_SCORE` | `0.8` | Score above which a payment is flagged |
| `COMPLIANCE_ENABLED` | `true` | Toggle full compliance pipeline |
| `SANCTIONS_CHECK_ENABLED` | `true` | Toggle SDN fuzzy match |
| `OFFLINE_MODE_ENABLED` | `true` | Allow payments to queue when network is unavailable |
| `ALCHEMY_API_KEY` | required | Must be set; app fails loudly at startup if missing |

---

## Running Both Apps

```bash
# App B — production stack (recommended starting point)
python -m uvicorn applications.capp.capp.main:app --reload --port 8000
# Docs: http://localhost:8000/docs

# App A — demo/legacy stack (sandbox tools, direct chain ops)
python -m uvicorn apps.api.app.main:app --reload --port 8001
# Docs: http://localhost:8001/docs
```

Required: `DATABASE_URL` (Postgres), `REDIS_URL`, `ALCHEMY_API_KEY`. See `env.example` at repo root.

MCP server:
```bash
CAPP_API_URL=http://localhost:8000/api/v1 python applications/capp/mcp_server/server.py
```
