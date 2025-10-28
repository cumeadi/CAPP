# M-Pesa Integration Guide

## Overview

M-Pesa is the leading mobile money service in East Africa, operated by Safaricom (Kenya), Vodacom (Tanzania), and Vodafone (Uganda). This integration supports all major M-Pesa transaction types.

## Supported Countries

| Country | Operator | Currency | Phone Format |
|---------|----------|----------|--------------|
| Kenya 🇰🇪 | Safaricom | KES | 254XXXXXXXXX |
| Tanzania 🇹🇿 | Vodacom | TZS | 255XXXXXXXXX |
| Uganda 🇺🇬 | Vodafone | UGX | 256XXXXXXXXX |

## Transaction Types

### 1. STK Push (Lipa Na M-Pesa Online)
Customer-initiated payment where a payment prompt is sent to the customer's phone.

**Use Cases:**
- E-commerce checkout
- Bill payments
- Service payments
- Subscriptions

**Flow:**
```
1. Merchant initiates STK Push
2. Customer receives payment prompt on phone
3. Customer enters M-Pesa PIN
4. Transaction is processed
5. Merchant receives callback with result
```

### 2. B2C (Business to Customer)
Business-initiated payment to send money to a customer.

**Use Cases:**
- Salary disbursements
- Refunds
- Rewards/Cashback
- Commission payments

**Flow:**
```
1. Business initiates B2C payment
2. M-Pesa processes transfer
3. Customer receives money
4. Business receives callback with result
```

### 3. C2B (Customer to Business)
Customer-initiated payment using Pay Bill or Buy Goods.

**Use Cases:**
- Pay Bill payments
- Buy Goods payments
- Utility bill payments
- Merchant payments

**Flow:**
```
1. Customer initiates payment via M-Pesa app
2. Customer enters Business Short Code
3. Customer enters account/reference number
4. Customer confirms with PIN
5. Business receives confirmation callback
```

---

## Getting Started

### Step 1: Register on Daraja Portal

1. Visit [https://developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Create an account
3. Create a new app
4. Note your **Consumer Key** and **Consumer Secret**

### Step 2: Configure Business Short Code

For production:
1. Contact Safaricom to get a Pay Bill or Till Number
2. Request API activation
3. Obtain your **Passkey**

For sandbox testing:
- **Business Short Code**: 174379
- **Passkey**: (provided in Daraja portal)

### Step 3: Set Environment Variables

```bash
# M-Pesa Configuration
export MMO_MPESA_CONSUMER_KEY="your_consumer_key_here"
export MMO_MPESA_CONSUMER_SECRET="your_consumer_secret_here"
export MMO_MPESA_BUSINESS_SHORT_CODE="174379"  # Use your own in production
export MMO_MPESA_PASSKEY="your_passkey_here"

# Optional: Specify environment
export MPESA_ENVIRONMENT="sandbox"  # or "production"
```

### Step 4: Initialize the Service

```python
from applications.capp.capp.services.mpesa_service import MpesaService

# Initialize service (reads from environment variables)
mpesa = MpesaService()
```

---

## Usage Examples

### STK Push Payment

```python
from applications.capp.capp.services.mpesa_service import MpesaService

# Initialize service
mpesa = MpesaService()

# Initiate STK Push
result = await mpesa.stk_push(
    phone_number="254708374149",
    amount=1000.00,
    account_reference="ORDER_12345",
    transaction_desc="Payment for Order 12345"
)

if result["success"]:
    checkout_request_id = result["checkout_request_id"]
    print(f"STK Push initiated: {checkout_request_id}")
    # Wait for callback...
else:
    print(f"Error: {result['error_message']}")
```

### Query STK Push Status

```python
# Query transaction status
status = await mpesa.query_stk_push(
    checkout_request_id="ws_CO_191220191020363925"
)

print(f"Status: {status['status']}")
print(f"Result Code: {status['result_code']}")
```

### B2C Disbursement

```python
# Send money to customer
result = await mpesa.b2c_payment(
    phone_number="254708374149",
    amount=5000.00,
    occasion="Salary Payment",
    remarks="Monthly Salary - January 2024",
    command_id="BusinessPayment"  # or "SalaryPayment", "PromotionPayment"
)

if result["success"]:
    print(f"B2C initiated: {result['conversation_id']}")
else:
    print(f"Error: {result['error_message']}")
```

### C2B Validation & Confirmation

C2B payments are received via webhooks. Set up your endpoints:

```python
from fastapi import APIRouter, Request
from applications.capp.capp.api.v1.endpoints import webhooks

router = APIRouter()

@router.post("/mpesa/c2b/validation")
async def c2b_validation(request: Request):
    """Validate C2B payment before processing"""
    data = await request.json()

    # Add your validation logic
    # Return ResultCode 0 to accept, non-zero to reject

    return {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }

@router.post("/mpesa/c2b/confirmation")
async def c2b_confirmation(request: Request):
    """Receive C2B payment confirmation"""
    data = await request.json()

    # Process confirmed payment
    transaction_id = data["TransID"]
    amount = data["TransAmount"]
    phone = data["MSISDN"]

    # Update your database
    await save_payment(transaction_id, amount, phone)

    return {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }
```

---

## Webhook Configuration

### STK Push Callback

Configure your callback URL in the Daraja Portal:

```
https://your-domain.com/v1/webhooks/mpesa/stkpush
```

**Callback Structure:**

```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_191220191020363925",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 1000.00},
          {"Name": "MpesaReceiptNumber", "Value": "NLJ7RT61SV"},
          {"Name": "TransactionDate", "Value": 20191219102115},
          {"Name": "PhoneNumber", "Value": 254708374149}
        ]
      }
    }
  }
}
```

### B2C Result Callback

```
https://your-domain.com/v1/webhooks/mpesa/b2c/result
```

### C2B Confirmation

```
https://your-domain.com/v1/webhooks/mpesa/c2b/confirmation
```

---

## Result Codes

### Common Result Codes

| Code | Description | Action |
|------|-------------|--------|
| 0 | Success | Transaction completed |
| 1 | Insufficient Funds | Customer has insufficient balance |
| 2001 | Invalid Phone Number | Phone number format incorrect |
| 1032 | Request Cancelled | Customer cancelled the request |
| 1037 | Timeout | Customer did not respond |
| 1 | General Error | Generic failure |
| 17 | System Busy | Retry later |
| 26 | Duplicate Request | Request already processed |
| 1001 | Invalid Credentials | Check Consumer Key/Secret |
| 1019 | Invalid Amount | Amount outside limits |

### Handling Result Codes

```python
def handle_mpesa_result(result_code: int) -> str:
    """Handle M-Pesa result codes"""
    if result_code == 0:
        return "success"
    elif result_code in [1, 2001]:
        return "failed"  # Don't retry
    elif result_code in [17, 1037]:
        return "retry"  # Can retry
    elif result_code == 1032:
        return "cancelled"  # Customer cancelled
    else:
        return "unknown"
```

---

## Error Handling

### Circuit Breaker

The service includes a circuit breaker to prevent cascade failures:

```python
from applications.capp.capp.services.mpesa_service import MpesaService

mpesa = MpesaService()

# Circuit breaker automatically opens after 5 failures
# Remains open for 60 seconds
# Then enters half-open state for testing

try:
    result = await mpesa.stk_push(...)
except CircuitBreakerError:
    print("M-Pesa service temporarily unavailable")
    # Use alternative payment method or queue for retry
```

### Retry Logic

Automatic retry with exponential backoff:

```python
# Automatically retries 3 times
# Delays: 2s, 4s, 8s
# Only retries on network errors and 503/504 responses

result = await mpesa.stk_push(
    phone_number="254708374149",
    amount=1000.00,
    account_reference="ORDER_12345",
    transaction_desc="Payment"
)
```

### Timeout Handling

```python
# Request timeout: 30 seconds
# If no response, returns timeout error
# Customer may still complete payment
# Always check status via query endpoint

result = await mpesa.stk_push(...)
if result["error_code"] == "TIMEOUT":
    # Query status after 60 seconds
    await asyncio.sleep(60)
    status = await mpesa.query_stk_push(result["checkout_request_id"])
```

---

## Testing

### Sandbox Testing

1. Use sandbox environment:
```bash
export MPESA_ENVIRONMENT="sandbox"
```

2. Test phone numbers:
```
254708374149  # Always succeeds
254111111111  # Always fails (insufficient funds)
254222222222  # Always times out
254333333333  # User cancels request
```

3. Test amounts:
```
1 - 70,000 KES  # Accepted range
```

### Integration Tests

Run the M-Pesa integration test suite:

```bash
# Run all M-Pesa tests
pytest tests/integration/test_mpesa_integration.py -v

# Run specific test
pytest tests/integration/test_mpesa_integration.py::test_stk_push_success -v

# Run with coverage
pytest tests/integration/test_mpesa_integration.py --cov=applications.capp.capp.services.mpesa_service
```

### Manual Testing

```python
import asyncio
from applications.capp.capp.services.mpesa_service import MpesaService

async def test_stk_push():
    mpesa = MpesaService()

    # Initiate STK Push
    result = await mpesa.stk_push(
        phone_number="254708374149",
        amount=10.00,  # Test with small amount
        account_reference="TEST_001",
        transaction_desc="Test payment"
    )

    print(f"Result: {result}")

    if result["success"]:
        # Wait for callback or query status
        await asyncio.sleep(30)
        status = await mpesa.query_stk_push(result["checkout_request_id"])
        print(f"Status: {status}")

# Run test
asyncio.run(test_stk_push())
```

---

## Production Checklist

### Pre-Production

- [ ] Register with Safaricom and obtain production credentials
- [ ] Get Business Short Code (Pay Bill or Till Number)
- [ ] Request API activation from Safaricom
- [ ] Obtain production Passkey
- [ ] Set up SSL/TLS certificates for webhook URLs
- [ ] Configure webhook URLs in Daraja Portal
- [ ] Test webhook endpoints are publicly accessible
- [ ] Implement signature verification (if available)
- [ ] Set up monitoring and alerting
- [ ] Configure structured logging

### Security

- [ ] Store credentials in environment variables or secrets manager
- [ ] Never commit credentials to version control
- [ ] Use HTTPS for all webhook URLs
- [ ] Implement rate limiting on webhook endpoints
- [ ] Validate all callback data before processing
- [ ] Log all transactions for audit trail
- [ ] Implement idempotency checks
- [ ] Set up fraud detection rules

### Operations

- [ ] Monitor transaction success rates
- [ ] Track response times (target: < 2s)
- [ ] Set up alerts for circuit breaker state
- [ ] Monitor callback processing errors
- [ ] Implement automated reconciliation
- [ ] Set up daily transaction reports
- [ ] Configure auto-scaling for high traffic
- [ ] Test disaster recovery procedures

---

## Transaction Limits

### M-Pesa Kenya

| Type | Minimum | Maximum | Fee |
|------|---------|---------|-----|
| STK Push | 1 KES | 150,000 KES | Tiered |
| B2C | 10 KES | 150,000 KES | Variable |
| C2B | 1 KES | 150,000 KES | Tiered |

### M-Pesa Tanzania

| Type | Minimum | Maximum | Fee |
|------|---------|---------|-----|
| STK Push | 100 TZS | 10,000,000 TZS | Tiered |
| B2C | 100 TZS | 10,000,000 TZS | Variable |

### M-Pesa Uganda

| Type | Minimum | Maximum | Fee |
|------|---------|---------|-----|
| STK Push | 500 UGX | 4,000,000 UGX | Tiered |
| B2C | 500 UGX | 4,000,000 UGX | Variable |

**Note**: Limits may vary based on customer verification level and business type.

---

## Common Issues

### Issue: "Invalid Access Token"
**Solution**: Access tokens expire after 1 hour. The service automatically refreshes them, but ensure your system time is synchronized.

### Issue: "Request Cancelled by User"
**Solution**: This is normal user behavior. Implement retry mechanism with user confirmation.

### Issue: "Timeout" (Result Code 1037)
**Solution**: Customer didn't respond within 60 seconds. Query transaction status after 2-3 minutes.

### Issue: "Insufficient Funds"
**Solution**: Customer doesn't have enough balance. Notify customer and suggest alternative payment.

### Issue: "Duplicate Request"
**Solution**: Transaction ID must be unique. Generate new ID for retries.

---

## Best Practices

### 1. Idempotency
Always use unique transaction IDs to prevent duplicate payments:

```python
import uuid

transaction_id = f"ORDER_{order_id}_{uuid.uuid4().hex[:8]}"
```

### 2. Status Polling
If callback is delayed, poll for status:

```python
async def wait_for_payment(checkout_request_id, max_attempts=6):
    """Poll payment status every 10 seconds"""
    for attempt in range(max_attempts):
        await asyncio.sleep(10)
        status = await mpesa.query_stk_push(checkout_request_id)
        if status["result_code"] is not None:
            return status
    return {"status": "timeout"}
```

### 3. Graceful Degradation
Handle M-Pesa downtime gracefully:

```python
try:
    result = await mpesa.stk_push(...)
except CircuitBreakerError:
    # Offer alternative payment methods
    return {
        "error": "M-Pesa temporarily unavailable",
        "alternatives": ["bank_transfer", "card_payment"]
    }
```

### 4. Transaction Reconciliation
Reconcile transactions daily:

```python
async def reconcile_transactions(date):
    """Match database records with M-Pesa statements"""
    db_transactions = await get_transactions(date)
    mpesa_statement = await mpesa.get_account_balance()

    # Compare and flag discrepancies
    discrepancies = []
    for txn in db_transactions:
        if not find_in_statement(txn, mpesa_statement):
            discrepancies.append(txn)

    return discrepancies
```

---

## Support & Resources

### Official Documentation
- Daraja API Docs: https://developer.safaricom.co.ke/docs
- API Sandbox: https://developer.safaricom.co.ke/test
- Status Page: https://status.safaricom.co.ke

### Support Channels
- Email: apisupport@safaricom.co.ke
- Phone: +254 711 051 555
- Portal: https://developer.safaricom.co.ke/support

### Community
- Developer Forum: https://developer.safaricom.co.ke/community
- Stack Overflow: Tag [mpesa-api]
- GitHub: https://github.com/safaricom

---

## Changelog

### v1.0.0 (2024-01-01)
- ✨ STK Push support
- ✨ B2C payment support
- ✨ C2B confirmation handling
- ✨ Circuit breaker pattern
- ✨ Automatic retry with exponential backoff
- ✨ Comprehensive error handling
- ✅ 35+ integration tests
