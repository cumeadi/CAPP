# MTN Mobile Money Integration Guide

## Overview

MTN Mobile Money (MoMo) is one of Africa's largest mobile money services, operating in 11+ countries across West, East, and Southern Africa. This integration supports Collections, Disbursements, and Remittances.

## Supported Countries

| Country | Currency | Phone Format | Code |
|---------|----------|--------------|------|
| Uganda 🇺🇬 | UGX | 256XXXXXXXXX | UG |
| Ghana 🇬🇭 | GHS | 233XXXXXXXXX | GH |
| Rwanda 🇷🇼 | RWF | 250XXXXXXXXX | RW |
| Zambia 🇿🇲 | ZMW | 260XXXXXXXXX | ZM |
| Nigeria 🇳🇬 | NGN | 234XXXXXXXXX | NG |
| Benin 🇧🇯 | XOF | 229XXXXXXXXX | BJ |
| Cameroon 🇨🇲 | XAF | 237XXXXXXXXX | CM |
| Congo-Brazzaville 🇨🇬 | XAF | 242XXXXXXXXX | CG |
| Côte d'Ivoire 🇨🇮 | XOF | 225XXXXXXXXX | CI |
| Guinea-Bissau 🇬🇼 | XOF | 245XXXXXXXXX | GW |
| Guinea-Conakry 🇬🇳 | GNF | 224XXXXXXXXX | GN |

## Products

### 1. Collection (Request to Pay)
Customer pays merchant - equivalent to "collect money from customer".

**Use Cases:**
- E-commerce payments
- Bill payments
- Service subscriptions
- Merchant payments

### 2. Disbursement (Transfer)
Merchant pays customer - equivalent to "send money to customer".

**Use Cases:**
- Salary payments
- Refunds
- Cashback/Rewards
- Vendor payments

### 3. Remittance
International money transfers between MTN MoMo accounts.

**Use Cases:**
- Cross-border transfers
- Family remittances
- Business payments across countries

---

## Getting Started

### Step 1: Register on MTN MoMo Developer Portal

1. Visit [https://momodeveloper.mtn.com](https://momodeveloper.mtn.com)
2. Create an account
3. Subscribe to the product (Collection, Disbursement, or Remittance)
4. Note your **Subscription Key** (Primary or Secondary)

### Step 2: Create API User & Key

For sandbox environment:

```bash
# Generate UUID for API User
export API_USER=$(uuidgen)

# Create API User
curl -X POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser \
  -H "X-Reference-Id: $API_USER" \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{"providerCallbackHost": "your-webhook-domain.com"}'

# Create API Key
curl -POST https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/$API_USER/apikey \
  -H "Ocp-Apim-Subscription-Key: YOUR_SUBSCRIPTION_KEY"
```

### Step 3: Set Environment Variables

```bash
# MTN Mobile Money Configuration
export MTN_MOMO_SUBSCRIPTION_KEY="your_subscription_key"
export MTN_MOMO_API_USER="your_api_user_uuid"
export MTN_MOMO_API_KEY="your_api_key"
export MTN_MOMO_ENVIRONMENT="sandbox"  # or "production"
```

### Step 4: Initialize the Service

```python
from applications.capp.capp.services.mtn_momo_integration import (
    MTNMoMoService,
    MTNMoMoProduct,
    MTNMoMoEnvironment
)

# Initialize service
mtn_service = MTNMoMoService(
    environment="sandbox"  # or "production"
)
```

---

## Usage Examples

### Request to Pay (Collection)

```python
# Customer pays merchant
result = await mtn_service.request_to_pay(
    phone_number="256774123456",
    amount=1000.0,
    currency="UGX",
    external_id="ORDER_12345",
    payer_message="Payment for Order 12345",
    payee_note="Thank you for your purchase"
)

if result["success"]:
    reference_id = result["reference_id"]
    print(f"Request to Pay initiated: {reference_id}")
    # Wait for callback or query status
else:
    print(f"Error: {result['message']}")
```

### Query Transaction Status

```python
from applications.capp.capp.services.mtn_momo_integration import MTNMoMoProduct

# Query Collection status
status = await mtn_service.get_transaction_status(
    reference_id="d4e90f52-7e4b-4f4a-9c3a-1234567890ab",
    product=MTNMoMoProduct.COLLECTION
)

print(f"Status: {status['status']}")  # PENDING, SUCCESSFUL, FAILED
if status['success'] and status['status'] == 'SUCCESSFUL':
    print(f"Receipt: {status['financialTransactionId']}")
```

### Transfer (Disbursement)

```python
# Merchant pays customer
result = await mtn_service.transfer(
    phone_number="256774123456",
    amount=5000.0,
    currency="UGX",
    external_id="SALARY_001",
    payee_note="January Salary Payment",
    payer_message="Salary Payment"
)

if result["success"]:
    print(f"Transfer initiated: {result['reference_id']}")
else:
    print(f"Error: {result['message']}")
```

### Remittance

```python
# International transfer
result = await mtn_service.remittance(
    phone_number="250788123456",  # Rwanda
    amount=10000.0,
    currency="RWF",
    external_id="REMIT_001",
    payer_message="Family support",
    payee_note="From Uganda"
)
```

---

## Webhook Configuration

### Collection Callback

Configure webhook URL:
```
https://your-domain.com/v1/webhooks/mtn/collection
```

**Callback Structure:**
```json
{
  "referenceId": "d4e90f52-7e4b-4f4a-9c3a-1234567890ab",
  "externalId": "ORDER_12345",
  "status": "SUCCESSFUL",
  "amount": "1000.00",
  "currency": "UGX",
  "financialTransactionId": "12345678",
  "payer": {
    "partyIdType": "MSISDN",
    "partyId": "256774123456"
  },
  "payerMessage": "Payment for Order 12345",
  "payeeNote": "Thank you"
}
```

### Disbursement Callback

```
https://your-domain.com/v1/webhooks/mtn/disbursement
```

### Remittance Callback

```
https://your-domain.com/v1/webhooks/mtn/remittance
```

---

## Status Codes

| Status | Description | Action |
|--------|-------------|--------|
| PENDING | Transaction is being processed | Wait for final status |
| SUCCESSFUL | Transaction completed successfully | Update order as paid |
| FAILED | Transaction failed | Check reason and handle |

## Error Reasons

| Reason | Description | Retryable |
|--------|-------------|-----------|
| PAYER_NOT_FOUND | Payer account doesn't exist | No |
| PAYEE_NOT_FOUND | Payee account doesn't exist | No |
| NOT_ALLOWED | Transaction not allowed | No |
| NOT_ENOUGH_FUNDS | Insufficient balance | No |
| PAYER_LIMIT_REACHED | Daily/monthly limit exceeded | No |
| PAYMENT_NOT_APPROVED | Customer rejected payment | No |
| RESOURCE_ALREADY_EXIST | Duplicate transaction ID | No |
| INTERNAL_PROCESSING_ERROR | System error | Yes |
| SERVICE_UNAVAILABLE | Service temporarily down | Yes |
| EXPIRED | Transaction expired | No |
| TRANSACTION_CANCELED | Transaction cancelled | No |

---

## Error Handling

### Circuit Breaker

Separate circuit breakers for each product:

```python
# Each product has independent circuit breaker
# - Opens after 5 consecutive failures
# - Timeout: 60 seconds
# - Then enters half-open state

try:
    result = await mtn_service.request_to_pay(...)
except CircuitBreakerError:
    # Circuit is open for Collection
    # But Disbursement might still work
    pass
```

### Retry Logic

```python
# Automatic retry on network errors
# - 3 attempts maximum
# - Exponential backoff: 2s, 4s, 8s
# - Only on retryable errors

result = await mtn_service.request_to_pay(...)
```

---

## Testing

### Sandbox Phone Numbers

```
256774123456  # Always succeeds (Uganda)
233244000000  # Always succeeds (Ghana)
250788123456  # Always succeeds (Rwanda)
260964000000  # Always succeeds (Zambia)
```

### Test Amounts

```
1 - 1,000,000  # Accepted range for most currencies
```

### Integration Tests

```bash
# Run MTN MoMo tests
pytest tests/integration/test_mtn_momo_integration.py -v

# Test specific scenario
pytest tests/integration/test_mtn_momo_integration.py::test_request_to_pay_success -v
```

---

## Production Checklist

- [ ] Register for production access on MTN MoMo portal
- [ ] Get production Subscription Key
- [ ] Create production API User and Key
- [ ] Configure production webhook URLs
- [ ] Test with real phone numbers in each country
- [ ] Set up monitoring for each product
- [ ] Implement rate limiting (600 req/min)
- [ ] Configure structured logging
- [ ] Set up reconciliation process
- [ ] Test circuit breaker behavior
- [ ] Document runbooks for common issues

---

## Transaction Limits

Varies by country and customer verification level.

### Uganda (UGX)
- Min: 1,000 UGX
- Max: 4,000,000 UGX per transaction
- Daily: 10,000,000 UGX

### Ghana (GHS)
- Min: 1 GHS
- Max: 10,000 GHS per transaction
- Daily: 50,000 GHS

### Rwanda (RWF)
- Min: 100 RWF
- Max: 5,000,000 RWF per transaction
- Daily: 10,000,000 RWF

**Note**: Limits increase with customer verification level (KYC).

---

## Best Practices

### 1. Unique Reference IDs
Always generate unique reference IDs using UUID:

```python
import uuid

reference_id = str(uuid.uuid4())
```

### 2. Status Polling
If callback is delayed, poll every 5 seconds:

```python
async def poll_status(reference_id, max_attempts=12):
    for attempt in range(max_attempts):
        await asyncio.sleep(5)
        status = await mtn_service.get_transaction_status(
            reference_id, MTNMoMoProduct.COLLECTION
        )
        if status["status"] != "PENDING":
            return status
    return {"status": "timeout"}
```

### 3. Token Caching
The service automatically caches OAuth2 tokens:

```python
# Token cached per product
# Auto-refreshes before expiration
# No manual token management needed
```

---

## Common Issues

### Issue: "Subscription key is invalid"
**Solution**: Verify your subscription key in MTN MoMo portal. Ensure you're using the correct environment (sandbox vs production).

### Issue: "API User not found"
**Solution**: Create API User using the `/apiuser` endpoint. Store the UUID.

### Issue: "PAYER_NOT_FOUND"
**Solution**: Phone number doesn't have MTN MoMo account. Verify number is correct and registered.

### Issue: "RESOURCE_ALREADY_EXIST"
**Solution**: Reference ID already used. Generate new UUID for each transaction.

---

## Support & Resources

### Official Documentation
- Developer Portal: https://momodeveloper.mtn.com
- API Documentation: https://momodeveloper.mtn.com/docs
- API Sandbox: https://momodeveloper.mtn.com/sandbox

### Support
- Email: api.support@mtn.com
- Portal: https://momodeveloper.mtn.com/support
- Status: https://status.mtn.com

---

## Changelog

### v1.0.0 (2024-01-01)
- ✨ Collection (Request to Pay) support
- ✨ Disbursement (Transfer) support
- ✨ Remittance support
- ✨ Per-product circuit breakers
- ✨ OAuth2 token caching per product
- ✨ 11+ country support
- ✅ 40+ integration tests
