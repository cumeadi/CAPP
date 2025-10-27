# Phase 3.2: Real MMO Integration Implementation Plan

## Executive Summary

This document outlines the comprehensive plan for implementing production-ready Mobile Money Operator (MMO) integrations for the CAPP platform. Currently, we have foundational implementations that need to be enhanced for production use with real API credentials, webhook handling, error recovery, and comprehensive testing.

**Status**: Phase 3A Complete (Database Integration) → Phase 3.2 In Progress (MMO Integration)

**Timeline**: 2-3 weeks
**Priority**: HIGH - Critical for processing real payments

---

## Current State Analysis

### ✅ What Exists

#### 1. M-Pesa Integration (`applications/capp/capp/services/mpesa_integration.py`)
- **Status**: Partial implementation, needs production hardening
- **Current Features**:
  - STK Push implementation
  - Payment status checking
  - Phone number formatting and validation
  - Access token management
  - Async/await architecture
- **Missing**:
  - Webhook callback handling
  - B2C (Business to Customer) disbursement
  - C2B (Customer to Business) registration
  - Comprehensive error retry logic
  - Production environment configuration
  - Database persistence for transactions

#### 2. MTN Mobile Money Integration (`packages/integrations/mobile_money/mtn_momo.py`)
- **Status**: Complete implementation, needs testing
- **Current Features**:
  - Collection (C2B) transactions
  - Disbursement (B2C) transactions
  - Account balance queries
  - Transaction status checking
  - Multi-country support (UG, GH, NG, RW, BI, ZM, MW, MZ, AO, NA, ZW)
  - Access token management
- **Missing**:
  - Webhook callback handling
  - Database persistence
  - Production testing
  - Error recovery mechanisms

#### 3. Airtel Money Integration (`packages/integrations/mobile_money/providers/airtel_money.py`)
- **Status**: Complete implementation, needs testing
- **Current Features**:
  - Transaction initiation
  - Phone number validation
  - Account balance queries
  - Multi-country support (12 countries)
  - Access token management
- **Missing**:
  - Webhook callback handling
  - Production testing
  - Enhanced error handling

#### 4. Orange Money Integration (`packages/integrations/mobile_money/orange_money.py`)
- **Status**: Not implemented (empty file)
- **Needs**: Complete implementation from scratch

#### 5. Base MMO Framework (`packages/integrations/mobile_money/base_mmo.py`)
- **Status**: Excellent foundation
- **Features**:
  - Abstract base class for all MMO integrations
  - Common interface (BaseMMOIntegration)
  - Transaction models (MMOTransaction, MMOBalance, MMOAccount)
  - Rate limiting
  - Redis caching
  - Mock implementation for testing

#### 6. Configuration (`applications/capp/capp/config/settings.py`)
- **Status**: Complete with placeholders
- **Features**:
  - Environment variable support for all MMO credentials
  - M-Pesa, Orange Money, MTN, Airtel configuration fields
  - SMS/USSD provider configuration

---

## Implementation Plan

### Priority 1: M-Pesa Production Readiness (Week 1)

M-Pesa is the most critical provider as it's the primary payment method in Kenya, our initial target market.

#### Task 1.1: Enhance M-Pesa Service Integration
**File**: `applications/capp/capp/services/mpesa_integration.py`

**Enhancements Needed**:
1. Add B2C disbursement support
2. Add C2B registration and validation
3. Implement retry logic with exponential backoff
4. Add circuit breaker pattern
5. Add database persistence for all transactions
6. Enhance error handling and logging
7. Add transaction timeout handling
8. Add idempotency support

**Code Structure**:
```python
class MpesaService:
    async def initiate_stk_push()  # ✅ Exists
    async def check_payment_status()  # ✅ Exists
    async def register_c2b_urls()  # ❌ Add
    async def initiate_b2c_payment()  # ❌ Add
    async def handle_callback()  # ❌ Add
    async def reverse_transaction()  # ❌ Add
    async def query_transaction()  # ❌ Add
```

#### Task 1.2: Add M-Pesa Webhook Handler
**New File**: `applications/capp/capp/api/webhooks/mpesa.py`

**Features**:
- FastAPI endpoint for M-Pesa callbacks
- Signature verification
- Callback data parsing
- Database updates
- Event publishing
- Retry handling

**API Endpoints**:
```python
POST /api/v1/webhooks/mpesa/stk-callback
POST /api/v1/webhooks/mpesa/c2b-confirmation
POST /api/v1/webhooks/mpesa/c2b-validation
POST /api/v1/webhooks/mpesa/timeout
```

#### Task 1.3: Add M-Pesa Database Models and Repositories
**File**: `applications/capp/capp/database/repositories/mpesa_repository.py`

**Models**:
- MpesaTransaction (STK Push tracking)
- MpesaCallback (Callback history)
- MpesaReversals (Transaction reversals)

**Repository Methods**:
```python
async def create_stk_push_request()
async def update_stk_push_status()
async def get_transaction_by_checkout_id()
async def save_callback()
async def get_transaction_history()
```

#### Task 1.4: M-Pesa Integration Tests
**File**: `tests/integration/test_mpesa_integration.py`

**Test Scenarios**:
- STK Push initiation
- Status checking
- Callback processing
- Error handling
- Retry logic
- Timeout handling

---

### Priority 2: MTN Mobile Money Production Readiness (Week 1-2)

MTN Mobile Money covers 11 African countries and is critical for regional expansion.

#### Task 2.1: Enhance MTN MoMo Service
**File**: `packages/integrations/mobile_money/mtn_momo.py`

**Enhancements**:
1. Add webhook callback handler
2. Add database persistence
3. Add remittance support
4. Enhance error handling
5. Add transaction reconciliation
6. Add country-specific business logic

#### Task 2.2: Add MTN MoMo Webhook Handler
**New File**: `applications/capp/capp/api/webhooks/mtn_momo.py`

**Endpoints**:
```python
POST /api/v1/webhooks/mtn-momo/collection
POST /api/v1/webhooks/mtn-momo/disbursement
POST /api/v1/webhooks/mtn-momo/remittance
```

#### Task 2.3: MTN MoMo Database Integration
**File**: `applications/capp/capp/database/repositories/mtn_repository.py`

**Features**:
- Transaction tracking
- Callback storage
- Balance history
- Reconciliation data

---

### Priority 3: Airtel Money Production Readiness (Week 2)

Airtel Money covers 12 African countries.

#### Task 3.1: Enhance Airtel Money Service
**File**: `packages/integrations/mobile_money/providers/airtel_money.py`

**Enhancements**:
1. Add webhook callback handler
2. Add database persistence
3. Complete disbursement flow
4. Add transaction reconciliation
5. Enhance error handling

#### Task 3.2: Add Airtel Money Webhook Handler
**New File**: `applications/capp/capp/api/webhooks/airtel_money.py`

#### Task 3.3: Airtel Money Database Integration
**File**: `applications/capp/capp/database/repositories/airtel_repository.py`

---

### Priority 4: Orange Money Implementation (Week 2-3)

Orange Money is essential for francophone African countries.

#### Task 4.1: Implement Orange Money Integration
**File**: `packages/integrations/mobile_money/orange_money.py`

**Requirements**:
- Extend BaseMMOIntegration
- Implement Orange Money API v2
- Support for francophone countries (CI, SN, ML, BF, NE, GN, CM, MG, CD)
- Collection and disbursement
- Transaction status checking

**API Structure**:
```python
class OrangeMoneyConfig(MMOConfig):
    provider: MMOProvider = MMOProvider.ORANGE_MONEY
    client_id: str
    client_secret: str
    merchant_key: str
    base_url: str = "https://api.orange.com/orange-money-webpay"

class OrangeMoneyIntegration(BaseMMOIntegration):
    async def _get_access_token()
    async def initiate_payment()
    async def check_transaction_status()
    async def get_account_balance()
```

#### Task 4.2: Orange Money Webhook Handler
**New File**: `applications/capp/capp/api/webhooks/orange_money.py`

#### Task 4.3: Orange Money Database Integration
**New File**: `applications/capp/capp/database/repositories/orange_repository.py`

---

### Priority 5: Unified MMO Service Layer (Week 3)

Create a unified service that abstracts all MMO providers for easy agent integration.

#### Task 5.1: Create MMO Service Manager
**New File**: `applications/capp/capp/services/mmo_service.py`

**Features**:
- Factory pattern for MMO provider selection
- Unified interface for all operations
- Automatic provider selection based on country/corridor
- Fallback provider logic
- Health monitoring

**Code Structure**:
```python
class MMOServiceManager:
    def __init__(self):
        self.providers = {
            "mpesa": MpesaService(),
            "mtn_momo": MTNMoMoIntegration(),
            "airtel_money": AirtelMoneyIntegration(),
            "orange_money": OrangeMoneyIntegration()
        }

    async def select_provider(self, country: str, currency: str) -> BaseMMOIntegration
    async def initiate_payment(self, payment: Payment) -> TransactionResult
    async def check_status(self, transaction_id: str, provider: str) -> TransactionStatus
    async def get_provider_health(self) -> Dict[str, HealthStatus]
```

#### Task 5.2: Integrate with Payment Orchestration
**File**: `applications/capp/capp/services/payment_orchestration.py`

**Changes**:
- Replace mock MMO calls with real MMO service
- Add provider selection logic
- Add transaction tracking
- Add error recovery

---

### Priority 6: Environment & Configuration Management (Week 3)

#### Task 6.1: Enhance Settings Configuration
**File**: `applications/capp/capp/config/settings.py`

**Additions**:
```python
# M-Pesa Extended
mpesa_base_url: str
mpesa_callback_url: str
mpesa_timeout_url: str
mpesa_environment: str  # sandbox, production
mpesa_initiator_name: str
mpesa_security_credential: str

# MTN MoMo Extended
mtn_subscription_key_collection: str
mtn_subscription_key_disbursement: str
mtn_subscription_key_remittance: str
mtn_target_environment: str
mtn_callback_url: str

# Airtel Money Extended
airtel_client_id: str
airtel_client_secret: str
airtel_environment: str
airtel_callback_url: str

# Orange Money
orange_client_id: str
orange_client_secret: str
orange_merchant_key: str
orange_environment: str
orange_callback_url: str
```

#### Task 6.2: Create Environment-Specific Config Files
**New Files**:
- `.env.development`
- `.env.sandbox`
- `.env.production`
- `.env.example`

---

### Priority 7: Testing & Validation (Week 3)

#### Task 7.1: Integration Tests
**Files**:
- `tests/integration/test_mpesa_integration.py`
- `tests/integration/test_mtn_momo_integration.py`
- `tests/integration/test_airtel_money_integration.py`
- `tests/integration/test_orange_money_integration.py`
- `tests/integration/test_mmo_service_manager.py`

**Test Coverage**:
- Happy path scenarios
- Error scenarios
- Timeout scenarios
- Retry logic
- Webhook processing
- Database persistence
- Provider failover

#### Task 7.2: End-to-End Payment Tests
**File**: `tests/e2e/test_real_mmo_payment_flow.py`

**Scenarios**:
- Kenya → Uganda via M-Pesa
- Nigeria → Ghana via MTN MoMo
- Kenya → Kenya via Airtel Money
- Côte d'Ivoire → Senegal via Orange Money

#### Task 7.3: Load Testing
**File**: `tests/load/test_mmo_performance.py`

**Metrics**:
- Concurrent payment processing
- Provider response times
- Error rates
- Recovery times

---

## Database Schema Changes

### New Tables

```sql
-- M-Pesa transactions
CREATE TABLE mpesa_transactions (
    id UUID PRIMARY KEY,
    payment_id UUID REFERENCES payments(id),
    checkout_request_id VARCHAR(255) UNIQUE,
    merchant_request_id VARCHAR(255),
    phone_number VARCHAR(20),
    amount DECIMAL(15,2),
    mpesa_receipt_number VARCHAR(255),
    transaction_date TIMESTAMP,
    status VARCHAR(50),
    result_code INTEGER,
    result_description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- MTN MoMo transactions
CREATE TABLE mtn_momo_transactions (
    id UUID PRIMARY KEY,
    payment_id UUID REFERENCES payments(id),
    reference_id VARCHAR(255) UNIQUE,
    external_id VARCHAR(255),
    financial_transaction_id VARCHAR(255),
    phone_number VARCHAR(20),
    amount DECIMAL(15,2),
    currency VARCHAR(3),
    transaction_type VARCHAR(50),  -- collection, disbursement, remittance
    status VARCHAR(50),
    country VARCHAR(3),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Airtel Money transactions
CREATE TABLE airtel_money_transactions (
    id UUID PRIMARY KEY,
    payment_id UUID REFERENCES payments(id),
    transaction_id VARCHAR(255) UNIQUE,
    reference VARCHAR(255),
    phone_number VARCHAR(20),
    amount DECIMAL(15,2),
    currency VARCHAR(3),
    status VARCHAR(50),
    country VARCHAR(3),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Orange Money transactions
CREATE TABLE orange_money_transactions (
    id UUID PRIMARY KEY,
    payment_id UUID REFERENCES payments(id),
    transaction_id VARCHAR(255) UNIQUE,
    order_id VARCHAR(255),
    phone_number VARCHAR(20),
    amount DECIMAL(15,2),
    currency VARCHAR(3),
    status VARCHAR(50),
    country VARCHAR(3),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- MMO callbacks (all providers)
CREATE TABLE mmo_callbacks (
    id UUID PRIMARY KEY,
    provider VARCHAR(50),
    transaction_id VARCHAR(255),
    callback_data JSONB,
    signature VARCHAR(500),
    verified BOOLEAN DEFAULT FALSE,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

### Webhook Endpoints

```
POST /api/v1/webhooks/mpesa/stk-callback
POST /api/v1/webhooks/mpesa/c2b-confirmation
POST /api/v1/webhooks/mpesa/c2b-validation
POST /api/v1/webhooks/mpesa/timeout

POST /api/v1/webhooks/mtn-momo/collection
POST /api/v1/webhooks/mtn-momo/disbursement
POST /api/v1/webhooks/mtn-momo/remittance

POST /api/v1/webhooks/airtel-money/callback
POST /api/v1/webhooks/airtel-money/status

POST /api/v1/webhooks/orange-money/callback
POST /api/v1/webhooks/orange-money/status
```

### Admin Endpoints

```
GET  /api/v1/admin/mmo/providers
GET  /api/v1/admin/mmo/providers/{provider}/health
GET  /api/v1/admin/mmo/providers/{provider}/stats
POST /api/v1/admin/mmo/providers/{provider}/test

GET  /api/v1/admin/mmo/transactions/{transaction_id}
GET  /api/v1/admin/mmo/transactions/{transaction_id}/callbacks
POST /api/v1/admin/mmo/transactions/{transaction_id}/retry
POST /api/v1/admin/mmo/transactions/{transaction_id}/reverse
```

---

## Success Criteria

### Technical Metrics
- ✅ All 4 MMO providers fully integrated (M-Pesa, MTN, Airtel, Orange)
- ✅ Webhook handling with 100% callback capture rate
- ✅ < 5 second average transaction initiation time
- ✅ < 2 second average status check time
- ✅ > 99.5% transaction success rate
- ✅ < 0.5% error rate with automatic recovery
- ✅ 100% database persistence for all transactions
- ✅ Sandbox and production environment support

### Testing Metrics
- ✅ > 90% code coverage for MMO integrations
- ✅ All integration tests passing
- ✅ All E2E tests passing
- ✅ Load tests handling 1000+ concurrent transactions
- ✅ Error recovery tests passing

### Documentation
- ✅ Complete API documentation for all MMO endpoints
- ✅ Webhook integration guide
- ✅ Environment setup guide
- ✅ Troubleshooting guide
- ✅ Testing guide

---

## Risk Mitigation

### Technical Risks

1. **MMO API Downtime**
   - Mitigation: Implement circuit breakers
   - Mitigation: Provider failover logic
   - Mitigation: Queue pending transactions

2. **Webhook Delivery Failures**
   - Mitigation: Implement active polling fallback
   - Mitigation: Retry logic with exponential backoff
   - Mitigation: Manual reconciliation tools

3. **Rate Limiting**
   - Mitigation: Request queuing
   - Mitigation: Multiple API keys rotation
   - Mitigation: Graceful degradation

4. **Data Consistency**
   - Mitigation: ACID transactions
   - Mitigation: Idempotency keys
   - Mitigation: Reconciliation jobs

### Business Risks

1. **High Transaction Fees**
   - Mitigation: Negotiate volume discounts
   - Mitigation: Route optimization
   - Mitigation: Dynamic provider selection

2. **Compliance Requirements**
   - Mitigation: Comprehensive audit logging
   - Mitigation: KYC data storage
   - Mitigation: Transaction limits enforcement

---

## Timeline & Milestones

### Week 1: M-Pesa & MTN Foundation
- Day 1-2: Enhance M-Pesa integration
- Day 3-4: M-Pesa webhook handling
- Day 5-7: MTN MoMo enhancements and webhooks

### Week 2: Airtel & Orange Implementation
- Day 8-10: Airtel Money enhancements and webhooks
- Day 11-14: Orange Money complete implementation

### Week 3: Integration & Testing
- Day 15-16: Unified MMO service layer
- Day 17-18: Integration tests
- Day 19-20: E2E tests and load testing
- Day 21: Documentation and deployment

---

## Next Steps

1. **Immediate**: Start with M-Pesa production enhancements (Task 1.1)
2. **This Week**: Complete M-Pesa integration and testing
3. **Next Week**: MTN and Airtel integration
4. **Week 3**: Orange Money and unified service layer

---

## Resources Required

### Development
- Real MMO API credentials for testing
- Sandbox environments for all providers
- Postman/Insomnia collections for testing
- Webhook testing tools (ngrok, webhook.site)

### Infrastructure
- Dedicated webhook endpoints (HTTPS required)
- Database storage for transactions
- Redis for caching and rate limiting
- Queue system for retry logic

### Documentation
- MMO provider API documentation
- Webhook integration guides
- Error code references
- Country-specific requirements

---

**Status**: Ready to begin implementation
**Next Action**: Start Task 1.1 - Enhance M-Pesa Service Integration
**Owner**: Development Team
**Last Updated**: 2025-10-27
