# CAPP — What It Does

**Canza Autonomous Payment Protocol (CAPP)** is an AI-powered infrastructure layer for African cross-border payments. It replaces manual routing decisions, fragmented MMO integrations, and slow bank rails with autonomous agents that find the cheapest, fastest, compliant path for every transaction — in real time.

---

## The Numbers

| Metric | CAPP | Traditional |
|---|---|---|
| Processing fees | ~0.8% | 8–9% |
| Settlement time | 1.5 seconds (on-chain) | 1–5 business days |
| Cost savings on a $1,000 transfer | **$8.10 saved** | baseline |
| Success rate | 95%+ | varies |
| Currencies supported | 40+ | varies by provider |
| Countries covered | 47 | varies |

---

## Who It's For

### Remittance operators and fintechs
You have a routing team, FX spreadsheets, and a patchwork of MMO API integrations. CAPP replaces that with a single API call. The Route Optimization Agent evaluates every available corridor in real time — cost, speed, reliability, live gas fees — and picks the best path. Compliance screening is automated. You don't need a routing team.

**What you get:**
- 15 African corridors live via HIFI Africa Rail
- 10 mobile money providers (M-Pesa, MTN MoMo, Orange Money, Airtel Money, Vodafone Cash, Tigo Pesa, Moov Money, EcoCash, M-Pesa Tanzania, M-Pesa Uganda)
- ACH and SWIFT rails
- Automated KYB/AML/sanctions/Travel Rule compliance
- Webhook notifications on every status change

**Pitch:** *"The cheapest, fastest route is chosen automatically. You don't need a routing team."*

---

### Banks and financial institutions
You need system-to-system integration with policy controls, auditable compliance, and batch processing. CAPP is built for that.

**What you get:**
- **Agent credential system** — issue API credentials to internal systems with per-transaction caps, daily limits, corridor allowlists, chain allowlists, and delegation hierarchy. A treasury department can hold a sub-credential that can only send to East Africa, capped at $50k/day.
- **Batch disbursements** — send payroll, supplier payments, or aid disbursements from a CSV. The agent groups by corridor, runs preflight balance checks, executes in parallel, and outputs a reconciliation report.
- **Compliance automation** — Travel Rule, SDN sanctions screening, PEP checks, adverse media, 7-year audit retention, CSV/PDF export.
- **Yield on idle settlement funds** — Smart Sweep deploys unused USDC to Aave V3 on Base/Arbitrum and withdraws just-in-time for settlement. Treasury earns while it waits.
- **Real-time event webhooks** — push payment status events to your core banking system.
- **Reconciliation** — internal ledger vs. live on-chain state comparison, alerts on drift above 0.01%.

**Pitch:** *"Plug CAPP into your treasury stack via API. Your agents operate autonomously within the policy limits you set."*

---

### Corporate treasury and payments infrastructure teams
You hold balances across multiple chains and currencies. You need FX rate certainty, yield on idle funds, and consolidated visibility.

**What you get:**
- **Multi-chain treasury dashboard** — real-time balances across Aptos, Polygon, Base, Arbitrum, and Starknet in a single API call.
- **FX rate locking** — rate locked at quote time with a configurable buffer.
- **AI market intelligence** — a Gemini-backed Market Analyst agent tracks chain congestion, gas volatility, and macro conditions to recommend optimal settlement timing.
- **Yield optimization** — the DeFi agent continuously monitors idle positions and moves them between Aave V3 and Yearn, withdrawing just-in-time when liquidity is needed.
- **FX arbitrage** — the Exchange Rate Agent aggregates rates from central banks, commercial banks, forex markets, and mobile money operators; detects spreads above 0.5% and acts on them.
- **Multi-currency support** — 40+ African currencies plus USD, EUR, GBP, and major crypto stablecoins.

**Pitch:** *"Your treasury earns while it waits. Settlement happens at the optimal moment, on the optimal chain."*

---

### Developers and platform builders
You're building a financial product and need African cross-border payments without rebuilding the infrastructure yourself.

**What you get:**
- **Three SDK layers** — pick the depth you need:
  - `capp-sdk` (Python) / `capp-sdk-ts` (TypeScript): direct HTTP client for the CAPP API
  - `packages/core`: multi-agent orchestration framework for building your own agents on top of CAPP
  - `sdk/` (Canza Agents): high-level `FinancialFramework` — point it at a region and risk profile, it handles the rest
- **MCP server** — CAPP as an AI tool for Claude, GPT, or any MCP-compatible agent framework. Tools: `analyze_routes`, `send_payment`, `get_balance`, `get_fx_rate`, `monitor_transaction`, `set_payment_policy`, `check_liquidity`.
- **9 runnable recipes** — production-ready agent examples in `capp-recipes/`:

| Recipe | What it does |
|---|---|
| 01 — Supplier Payment | Automated cross-border supplier payment with route optimization |
| 02 — Treasury Rebalancing | Multi-corridor liquidity rebalancing |
| 03 — Payroll Distribution | Bulk payroll from CSV across Nigeria, Kenya, Ghana and more |
| 04 — Payment-Triggered Workflow | Event-driven workflows on payment completion |
| 05 — Smart Escrow | Milestone-based fund release |
| 06 — Dollar-Cost Averaging | Scheduled recurring investment in target currencies |
| 07 — FX Arbitrage | Automated spread detection and execution |
| 08 — Subscription Churn Rescue | Retry failed subscription payments via alternate routes |
| 09 — Automated Hedging | FX exposure hedging with autonomous execution |
| 10 — DAO CFO | Autonomous treasury management for decentralized organizations |

- **Sandbox environment** — full testnet lifecycle: failure injection, state reset, testnet faucet, no real funds needed.
- **Developer portal** — Docusaurus site with quickstart guide and full API reference.

**Pitch:** *"Embed African cross-border payments in your product in a weekend. 10 ready-made agent recipes. Sandbox to production without changing your integration."*

---

## Live Corridors

### HIFI Africa Rail

| Country | Currency | Pay-in | Pay-out |
|---|---|---|---|
| Nigeria | NGN | ✓ | ✓ |
| Tanzania | TZS | ✓ | ✓ |
| Uganda | UGX | ✓ | ✓ |
| Zambia | ZMW | ✓ | ✓ |
| Cameroon | XAF | ✓ | ✓ |
| Côte d'Ivoire | XOF | ✓ | ✓ |
| Benin | XOF | ✓ | ✓ |
| Togo | XOF | ✓ | ✓ |
| Botswana | BWP | ✓ | ✓ |
| Malawi | MWK | ✓ | ✓ |
| Kenya | KES | — | ✓ |
| South Africa | ZAR | — | ✓ |
| Senegal | XOF | — | ✓ |
| Mali | XOF | — | ✓ |
| Burkina Faso | XOF | — | ✓ |

### Blockchain settlement
Aptos, Polygon, Base, Arbitrum, Ethereum, Optimism, Starknet

> Solana and Stellar integrations are in development (mock only). They are excluded from the production `Chain` enum and gated behind `ENABLE_MOCK_CHAINS=true`.

### Bridge providers
Stargate, Across, Hop, CCTP (Circle), Hyperlane, LayerZero, Li.Fi

---

## Supported Currencies

**West Africa:** NGN, XOF, GHS, GMD, SLL

**East Africa:** KES, UGX, TZS, RWF, BIF, ETB, SOS

**Southern Africa:** ZAR, ZMW, BWP, SZL, LSL, MWK, MZN, AOA, NAD

**Central Africa:** XAF, CDF

**North Africa:** EGP, MAD, TND, DZD, LYD, SDG

**International:** USD, EUR, GBP

**Crypto / Stablecoin:** USDC, ETH, APT, MATIC

---

## Mobile Money Providers

M-Pesa (Kenya), M-Pesa Tanzania, M-Pesa Uganda, MTN Mobile Money, Orange Money, Airtel Money, Vodafone Cash, Tigo Pesa, Moov Money, EcoCash

---

## Feature Summary

### Payments
- Cross-border transfers: personal remittance, business payment, merchant payment, airtime purchase, bill payment
- Bulk disbursement (payroll, supplier, aid)
- Payment cancellation (PENDING and PROCESSING states)
- Offline queuing with automatic sync when connectivity restores
- Idempotency keys for safe retries

### Routing and optimization
- Real-time multi-path route analysis across all supported chains and rails
- AI/RL route scoring: cost (40%), speed (30%), reliability (20%), compliance (10%)
- Route preferences: CHEAPEST, FASTEST, BALANCED
- FX rate aggregation from central banks, commercial banks, forex markets, and MMOs
- FX rate locking with configurable buffer

### Compliance
- KYC threshold screening ($1,000 trigger)
- AML screening ($3,000 trigger)
- Enhanced due diligence ($10,000 trigger)
- SDN sanctions list screening with fuzzy name matching
- PEP (Politically Exposed Person) checks
- Adverse media screening
- Travel Rule automation
- 7-year compliance record retention
- CSV and PDF report export

### Treasury and yield
- Smart Sweep: autonomous deployment of idle funds to Aave V3 (Base, Arbitrum) and Yearn
- Just-in-time liquidity withdrawal for settlement
- Multi-chain balance aggregation with USD valuation
- Real-time yield position tracking

### Agent controls
- Autonomy levels: COPILOT (all actions require approval), GUARDED (approval above threshold), SOVEREIGN (fully autonomous)
- Human-in-the-loop approval/rejection for high-value actions
- Per-credential spending caps (per-transaction and daily)
- Corridor and chain allowlists per credential
- Credential delegation (max 2 levels deep, permissions can only narrow)

### Developer
- REST API with Swagger/ReDoc interactive docs
- Python SDK (`capp-sdk`) and TypeScript SDK (`capp-sdk-ts`)
- MCP server for agent framework integration
- Webhook subscriptions with threshold filtering
- Sandbox environment: failure injection, state reset, testnet faucet
- Chaos engineering mode for resilience testing
