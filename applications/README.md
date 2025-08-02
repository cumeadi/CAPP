# Canza Platform Applications

This directory contains applications built with the Canza Platform.

## 📁 Structure

```
applications/
└── capp/                  # Canza Autonomous Payment Protocol
    ├── backend/           # FastAPI backend
    ├── frontend/          # React frontend
    ├── agents/            # Payment agents
    └── docs/              # Application documentation
```

## 🎯 CAPP Application

The **Canza Autonomous Payment Protocol (CAPP)** is the flagship application demonstrating the platform's capabilities:

### Features

- **End-to-End Payment Processing**: Complete payment flow from request to settlement
- **AI Agent Orchestration**: Intelligent agents coordinate payment optimization
- **Real-Time Optimization**: Route optimization and cost reduction
- **Multi-Currency Support**: 42+ African currencies
- **Blockchain Integration**: Aptos blockchain settlement
- **Mobile Money Integration**: USSD, SMS, and API connections
- **Analytics Dashboard**: Real-time metrics and insights

### Architecture

- **Backend**: FastAPI-based REST API with async processing
- **Frontend**: React-based user interface with real-time updates
- **Agents**: Autonomous payment optimization agents
- **Database**: PostgreSQL with async SQLAlchemy
- **Cache**: Redis for performance optimization
- **Monitoring**: Prometheus metrics and structured logging

### Quick Start

```bash
# Start the backend
cd applications/capp
python -m capp.main

# Start the frontend (in another terminal)
cd applications/capp/frontend
npm install
npm start
```

### API Endpoints

- `GET /health` - Health check
- `POST /api/v1/payments/send` - Send payment
- `GET /api/v1/payments/{payment_id}/status` - Payment status
- `GET /api/v1/payments/routes` - Available routes
- `GET /api/v1/payments/rates` - Exchange rates

### Documentation

- [User Guide](capp/docs/user-guide.md)
- [API Reference](capp/docs/api-reference.md)
- [Deployment Guide](capp/docs/deployment.md)

## 🚀 Building New Applications

To build a new application using the Canza Platform:

1. **Create a new directory** in `applications/`
2. **Use the shared packages** from `packages/`
3. **Leverage the SDK** from `sdk/`
4. **Follow the established patterns** from CAPP
5. **Add comprehensive documentation**

### Example Structure

```
applications/my-app/
├── backend/               # Application backend
├── frontend/              # Application frontend
├── agents/                # Custom agents
├── tests/                 # Test suite
├── docs/                  # Documentation
├── requirements.txt       # Dependencies
└── README.md             # Application guide
```

## 📄 License

Applications are licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 