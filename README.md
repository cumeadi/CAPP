# CAPP - Canza Autonomous Payment Protocol
[![GitBook](https://img.shields.io/static/v1?message=Documented%20on%20GitBook&logo=gitbook&logoColor=ffffff&label=%20&labelColor=5c5c5c&color=3F89A1)](https://www.gitbook.com/preview?utm_source=gitbook_readme_badge&utm_medium=organic&utm_campaign=preview_documentation&utm_content=link)

A revolutionary AI-powered payment system for African cross-border commerce, featuring autonomous agents that optimize payment routes, reduce costs, and accelerate settlements in real-time.

## 🚀 Quick Start

### Option 1: One-Command Startup
```bash
./start-capp.sh
```

### Option 2: Manual Setup
```bash
# Backend
source venv/bin/activate
python -m uvicorn apps.api.app.main:app --reload --port 8000

# Frontend (Web App) - in another terminal
cd apps/web
npm run dev

# Wallet App - in another terminal (optional)
cd apps/wallet
npm run dev
```

## 📊 Demo Results

Our Nigeria → Kenya payment demonstration shows:
- **91% Cost Reduction**: From 8.9% to 0.8% processing fees
- **1.5 Second Settlement**: Down from 3 days traditional processing
- **172,291x Speed Improvement**: Real-time optimization vs manual processes
- **$8.10 Saved**: On a $1,000 transaction

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **Agent-Based Architecture**: Autonomous agents coordinate payment flows and cross-chain operations.
- **Intelligent Routing Engine**: Optimizes payment paths based on real-time gas/fees from Aptos, Polygon, and Starknet.
- **Event-Driven**: Apache Kafka for reliable cross-border messaging (mocked/simulated in dev).
- **Blockchain Integration**: Real-time integration with Aptos, Polygon, and Starknet.
- **Yield Service**: Smart Sweep functionality for idle assets.

### Frontend (Next.js + TypeScript)
- **Modern Web Architecture**: Built with Next.js 15+ for server-side rendering and performance.
- **Dual Applications**:
  - **Web App (`apps/web`)**: Main platform interface, dashboard, and payment demo.
  - **Wallet App (`apps/wallet`)**: Personal crypto wallet interface.
- **Styling**: Tailwind CSS for utility-first design.
- **Interactive Visuals**: Framer Motion for animations.

## 🎯 Core Features

### Autonomous Payment Agents
1. **Route Optimization Agent**: Finds optimal payment corridors across supported chains.
2. **Liquidity Management Agent**: Manages liquidity pools and reservations.
3. **Settlement Agent**: Handles blockchain settlement operations.
4. **Compliance Agent**: Multi-jurisdiction compliance validation (KYB-as-a-Service).
5. **Relayer Agent**: Automates cross-chain bridging.

### Payment Optimization
- **Smart Sweep**: Automatically routes idle funds to yield-generating protocols.
- **Real-Time Route Analysis**: Uses live chain data for optimal pathfinding.
- **Cost Optimization**: Fee minimization across providers.
- **Compliance Automation**: Automated Travel Rule checks and risk scoring.

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Async web framework
- **SQLAlchemy + Alembic**: Database ORM and migrations
- **PostgreSQL**: Primary data store
- **Redis**: Caching and rate limiting
- **Aptos SDK / Web3.py / Starknet.py**: Blockchain interaction
- **Structlog**: Structured logging

### Frontend
- **Next.js**: React Framework for Production
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Styling
- **Framer Motion**: Animations
- **Lucide React**: Icons
- **Wagmi / Viem**: Ethereum hooks and utils
- **Starknet.js**: Starknet interaction

## 📁 Project Structure

```
capp/
├── apps/                          # Application source code
│   ├── api/                      # Backend API (FastAPI)
│   │   ├── app/                  # Application logic
│   │   └── ...
│   ├── web/                      # Main Frontend (Next.js)
│   │   ├── app/                  # App Router pages
│   │   └── ...
│   └── wallet/                   # Wallet Application (Next.js)
│       └── ...
├── packages/                      # Shared packages
│   ├── core/                     # Core business logic
│   └── integrations/             # External service wrappers
├── scripts/                       # DevOps and maintenance scripts
├── docker-compose.yml            # Container orchestration
├── start-capp.sh                 # Startup helper
└── README.md                     # This file
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis (optional but recommended)

### Backend Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r apps/api/requirements.txt (or root requirements.txt if using monorepo style)

# Set up environment variables
cp .env.example .env

# Run migrations
alembic upgrade head

# Run backend
python -m uvicorn apps.api.app.main:app --reload
```

### Frontend Setup
```bash
# Navigate to web app
cd apps/web

# Install dependencies
npm install

# Start development server
npm run dev
```

## 🌐 API Endpoints

### Payment Operations
- `POST /api/v1/payments/send` - Send payment
- `GET /api/v1/routing/analyze` - Analyze routes
- `GET /api/v1/wallet/balance` - Get real-time balances

### Health & Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /docs` - Interactive API documentation

## 🎯 Roadmap & Status

### Phase 1: Security Hardening ✅
- [x] CORS, JWT, Rate Limiting, Input Validation

### Phase 2: Core Implementation ✅
- [x] Database layer & Migrations
- [x] User & Payment Repositories
- [x] Basic Agent Architecture

### Phase 3: Real Wallets & Integration (Current)
- [x] Aptos Real Balance Integration
- [x] Intelligent Routing Engine (Gas estimation)
- [x] Yield Service (Smart Sweep)
- [x] Relayer Agents (Cross-chain)
- [ ] Full Mainnet Settlement

### Phase 4: Production Polish
- [ ] System Health Monitoring
- [ ] Advanced Error Handling
- [ ] Analytics Service
- [ ] Production Deployment (Docker/K8s)

---

**CAPP** - Transforming African cross-border payments with autonomous AI agents. 
