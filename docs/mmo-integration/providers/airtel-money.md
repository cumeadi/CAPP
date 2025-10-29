# Airtel Money Integration Guide

## Overview

Airtel Money is a leading mobile money service operating across 14+ African countries. This integration supports Push Payments (merchant to customer) and Disbursements (bulk payouts) with real-time transaction processing.

## Supported Countries

| Country | Currency | Phone Format | Code |
|---------|----------|--------------|------|
| Kenya 🇰🇪 | KES | 254XXXXXXXXX | KE |
| Tanzania 🇹🇿 | TZS | 255XXXXXXXXX | TZ |
| Uganda 🇺🇬 | UGX | 256XXXXXXXXX | UG |
| Rwanda 🇷🇼 | RWF | 250XXXXXXXXX | RW |
| Zambia 🇿🇲 | ZMW | 260XXXXXXXXX | ZM |
| Malawi 🇲🇼 | MWK | 265XXXXXXXXX | MW |
| Nigeria 🇳🇬 | NGN | 234XXXXXXXXX | NG |
| Ghana 🇬🇭 | GHS | 233XXXXXXXXX | GH |
| Chad 🇹🇩 | XAF | 235XXXXXXXXX | TD |
| Niger 🇳🇪 | XOF | 227XXXXXXXXX | NE |
| Congo-Brazzaville 🇨🇬 | XAF | 242XXXXXXXXX | CG |
| Democratic Republic of Congo 🇨🇩 | CDF | 243XXXXXXXXX | CD |
| Gabon 🇬🇦 | XAF | 241XXXXXXXXX | GA |
| Madagascar 🇲🇬 | MGA | 261XXXXXXXXX | MG |

## Transaction Types

### 1. Push Payment
Merchant-initiated payment where customer receives money.

**Use Cases:**
- Customer refunds
- Cashback rewards
- Promotional payments
- Voucher redemptions

### 2. Disbursement
Bulk payout to multiple recipients.

**Use Cases:**
- Salary payments
- Vendor payments
- Commission payouts
- Agent float management

---

## Getting Started

### Step 1: Register on Airtel Money for Businesses

1. Contact Airtel Money Business team in your country
2. Complete business registration
3. Receive API credentials:
   - Client ID
   - Client Secret
   - API Key

### Step 2: Set Environment Variables

```bash
# Airtel Money Configuration
export AIRTEL_MONEY_CLIENT_ID="your_client_id"
export AIRTEL_MONEY_CLIENT_SECRET="your_client_secret"
export AIRTEL_MONEY_API_KEY="your_api_key"
export AIRTEL_MONEY_ENVIRONMENT="staging"  # or "production"
```

### Step 3: Initialize the Service

```python
from applications.capp.capp.services.airtel_money_integration import AirtelMoneyService

# Initialize service
airtel_service = AirtelMoneyService(
    environment="staging"  # or "production"
)
```

---

## Usage Examples

### Push Payment

```python
# Send money to customer
result = await airtel_service.push_payment(
    phone_number="254700123456",
    amount=1000.0,
    currency="KES",
    transaction_id="REFUND_12345",
    country_code="KE"
)

if result["success"]:
    transaction_id = result["transaction_id"]
    print(f"Push payment initiated: {transaction_id}")
    print(f"Status: {result['status']}")  # TS, TIP, or TF
else:
    print(f"Error: {result['message']}")
```

### Disbursement

```python
# Bulk payout
result = await airtel_service.disbursement(
    phone_number="254700123456",
    amount=5000.0,
    currency="KES",
    transaction_id="SALARY_001",
    country_code="KE"
)

if result["success"]:
    print(f"Disbursement initiated: {result['transaction_id']}")
else:
    print(f"Error: {result['message']}")
```

### Query Transaction Status

```python
# Check transaction status
status = await airtel_service.get_transaction_status(
    transaction_id="REFUND_12345",
    country_code="KE"
)

print(f"Status: {status['status']}")  # TS, TIP, TF, TA, TU
print(f"Message: {status.get('message', 'N/A')}")
```

---

## Webhook Configuration

### Payment Callback

Configure webhook URL:
```
https://your-domain.com/v1/webhooks/airtel/payment
```

**Callback Structure:**
```json
{
  "transaction": {
    "id": "airtel_txn_123456789",
    "status": "TS",
    "message": "Transaction processed successfully"
  },
  "data": {
    "transaction": {
      "id": "REFUND_12345",
      "amount": "1000.00",
      "currency": "KES",
      "status": "TS",
      "message": "Success"
    }
  }
}
```

**Response Format:**
```json
{
  "status": {
    "code": "200",
    "message": "Callback received successfully",
    "success": true
  }
}
```

### Disbursement Callback

```
https://your-domain.com/v1/webhooks/airtel/disbursement
```

### Notification Callback

```
https://your-domain.com/v1/webhooks/airtel/notification
```

---

## Status Codes

| Code | Description | Final Status |
|------|-------------|--------------|
| TS | Transaction Successful | Yes |
| TIP | Transaction In Progress | No |
| TF | Transaction Failed | Yes |
| TA | Transaction Ambiguous | No |
| TU | Transaction Unknown | No |

### Status Handling

```python
def handle_airtel_status(status_code: str) -> str:
    """Handle Airtel Money status codes"""
    if status_code == "TS":
        return "completed"
    elif status_code == "TIP":
        return "pending"  # Poll for final status
    elif status_code == "TF":
        return "failed"
    elif status_code in ["TA", "TU"]:
        return "unknown"  # Query transaction status
    else:
        return "unknown"
```

---

## Error Codes

| Error Code | Description | Retryable |
|------------|-------------|-----------|
| DP00800001007 | Insufficient Balance | No |
| DP00800001009 | Invalid MSISDN | No |
| DP00800001010 | Invalid Amount | No |
| DP00800001011 | Maximum transaction limit exceeded | No |
| DP00800001013 | Duplicate transaction | No |
| DP00800001014 | Transaction not found | No |
| DP00800001015 | Transaction expired | No |
| DP00800001016 | Subscriber not found | No |
| DP00800001017 | Invalid currency | No |
| DP00800001018 | Transaction declined | No |
| DP00800001019 | Service unavailable | Yes |
| DP00800001020 | System error | Yes |

---

## Error Handling

### Circuit Breaker

```python
# Single circuit breaker for all operations
# - Opens after 5 consecutive failures
# - Timeout: 60 seconds
# - Then enters half-open state

try:
    result = await airtel_service.push_payment(...)
except CircuitBreakerError:
    print("Airtel Money temporarily unavailable")
    # Queue for retry or use alternative provider
```

### Retry Logic

```python
# Automatic retry with exponential backoff
# - 3 attempts maximum
# - Delays: 2s, 4s, 8s
# - Only on network errors and retryable error codes

result = await airtel_service.push_payment(...)
```

### OAuth2 Token Management

```python
# Token automatically refreshed
# - Cached until expiration
# - Client credentials grant
# - No manual refresh needed

# Token refresh happens automatically
result = await airtel_service.push_payment(...)
```

---

## Testing

### Staging Environment

```bash
export AIRTEL_MONEY_ENVIRONMENT="staging"
```

### Test Phone Numbers

```
254700123456  # Kenya - Always succeeds
255700123456  # Tanzania - Always succeeds
256774123456  # Uganda - Always succeeds
250788123456  # Rwanda - Always succeeds
```

### Test Amounts

```
10 - 100,000  # Accepted range for testing
```

### Integration Tests

```bash
# Run Airtel Money tests
pytest tests/integration/test_airtel_money_integration.py -v

# Test specific scenario
pytest tests/integration/test_airtel_money_integration.py::test_push_payment_success -v

# Test with coverage
pytest tests/integration/test_airtel_money_integration.py --cov
```

---

## Production Checklist

- [ ] Complete business registration with Airtel Money
- [ ] Receive production credentials
- [ ] Test in staging environment first
- [ ] Configure production webhook URLs
- [ ] Set up SSL/TLS certificates
- [ ] Test with real phone numbers in each country
- [ ] Implement rate limiting
- [ ] Configure monitoring and alerts
- [ ] Set up reconciliation process
- [ ] Test disaster recovery procedures
- [ ] Document escalation procedures

---

## Transaction Limits

Limits vary by country and customer KYC level.

### Kenya (KES)
- Min: 10 KES
- Max: 150,000 KES per transaction
- Daily: 300,000 KES

### Tanzania (TZS)
- Min: 1,000 TZS
- Max: 5,000,000 TZS per transaction
- Daily: 10,000,000 TZS

### Uganda (UGX)
- Min: 1,000 UGX
- Max: 4,000,000 UGX per transaction
- Daily: 10,000,000 UGX

### Rwanda (RWF)
- Min: 100 RWF
- Max: 2,000,000 RWF per transaction
- Daily: 5,000,000 RWF

**Note**: Limits are higher for verified business accounts.

---

## Best Practices

### 1. Unique Transaction IDs
Generate unique transaction IDs for each request:

```python
import uuid
from datetime import datetime

# Include timestamp for uniqueness
transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
```

### 2. Status Polling
For TIP (In Progress) status, poll every 5 seconds:

```python
async def wait_for_completion(transaction_id, country_code, max_attempts=12):
    """Poll until final status"""
    for attempt in range(max_attempts):
        await asyncio.sleep(5)
        status = await airtel_service.get_transaction_status(
            transaction_id, country_code
        )

        if status["status"] in ["TS", "TF"]:
            return status

        if attempt == max_attempts - 1:
            return {"status": "timeout"}

    return status
```

### 3. Country-Specific Handling
Different countries may have different behaviors:

```python
# Kenya might process faster than Tanzania
# Adjust polling intervals accordingly

country_poll_intervals = {
    "KE": 3,  # 3 seconds
    "TZ": 5,  # 5 seconds
    "UG": 5,
    "RW": 5
}
```

### 4. Error Recovery
Handle temporary failures gracefully:

```python
async def retry_with_fallback(transaction_id, max_retries=3):
    """Retry with exponential backoff"""
    for retry in range(max_retries):
        try:
            result = await airtel_service.push_payment(...)
            return result
        except Exception as e:
            if retry == max_retries - 1:
                # Use alternative payment method
                return await fallback_payment_method(...)

            await asyncio.sleep(2 ** retry)  # 1s, 2s, 4s
```

---

## Common Issues

### Issue: "Invalid MSISDN" (DP00800001009)
**Solution**: Ensure phone number is in international format without + or 00 prefix.
```python
# Correct: "254700123456"
# Wrong: "+254700123456" or "0700123456"
```

### Issue: "Duplicate transaction" (DP00800001013)
**Solution**: Transaction ID already used. Generate new unique ID for retries.

### Issue: "Subscriber not found" (DP00800001016)
**Solution**: Phone number doesn't have Airtel Money account or not registered in that country.

### Issue: "Service unavailable" (DP00800001019)
**Solution**: Temporary service outage. Retry after 60 seconds or use circuit breaker pattern.

### Issue: Token expired
**Solution**: Service automatically refreshes tokens. If manual refresh needed:
```python
# Token auto-refreshed on next API call
result = await airtel_service.push_payment(...)
```

---

## Multi-Country Deployment

### Country-Specific Configuration

```python
# Different API endpoints per country
country_configs = {
    "KE": {"endpoint": "kenya", "currency": "KES"},
    "TZ": {"endpoint": "tanzania", "currency": "TZS"},
    "UG": {"endpoint": "uganda", "currency": "UGX"},
    "RW": {"endpoint": "rwanda", "currency": "RWF"}
}

# Route based on country
async def process_payment(phone, amount, country):
    config = country_configs[country]
    return await airtel_service.push_payment(
        phone_number=phone,
        amount=amount,
        currency=config["currency"],
        transaction_id=generate_id(),
        country_code=country
    )
```

### Load Balancing

```python
# Distribute load across countries
from collections import defaultdict

request_counts = defaultdict(int)

async def balanced_payment(phone, amount, country):
    """Rate limit per country"""
    if request_counts[country] > 100:  # per minute
        await asyncio.sleep(1)

    request_counts[country] += 1
    return await process_payment(phone, amount, country)
```

---

## Monitoring & Alerts

### Key Metrics

```python
# Track these metrics
metrics = {
    "total_transactions": 0,
    "successful_transactions": 0,
    "failed_transactions": 0,
    "avg_response_time": 0,
    "circuit_breaker_state": "CLOSED",
    "token_refresh_count": 0
}

# Alert thresholds
alerts = {
    "success_rate_below": 0.95,  # Alert if < 95%
    "avg_response_above": 5.0,   # Alert if > 5 seconds
    "circuit_breaker_open": True # Alert immediately
}
```

### Logging

```python
import structlog

logger = structlog.get_logger()

# Log all transactions
logger.info(
    "airtel_payment_initiated",
    transaction_id=transaction_id,
    phone_number=phone[-4:],  # Last 4 digits only
    amount=amount,
    currency=currency,
    country=country_code
)
```

---

## Support & Resources

### Official Documentation
- Business Portal: https://business.airtel.com
- API Documentation: https://developers.airtel.com/documentation
- Integration Guide: https://developers.airtel.com/integration-guide

### Support Channels
- Email: business.support@airtel.com
- Phone: Contact local Airtel Money team
- Portal: https://business.airtel.com/support

### Developer Community
- Forum: https://community.airtel.com
- Stack Overflow: Tag [airtel-money]

---

## Changelog

### v1.0.0 (2024-01-01)
- ✨ Push Payment support
- ✨ Disbursement support
- ✨ Status query API
- ✨ 14+ country support
- ✨ OAuth2 with automatic refresh
- ✨ Circuit breaker pattern
- ✨ Retry logic with exponential backoff
- ✅ 35+ integration tests
- ✅ Multi-country test coverage
