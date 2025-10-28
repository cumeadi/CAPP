# MMO API Endpoints

## Base URL

```
Production: https://api.capp.com/v1
Staging: https://staging-api.capp.com/v1
Development: http://localhost:8000/v1
```

## Authentication

All endpoints require Bearer token authentication:

```http
Authorization: Bearer <your_access_token>
```

## Webhook Endpoints

### M-Pesa Webhooks

#### STK Push Callback
Receives M-Pesa STK Push (Lipa Na M-Pesa Online) transaction results.

```http
POST /webhooks/mpesa/stkpush
Content-Type: application/json
```

**Request Body:**
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

**Response:**
```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

**Result Codes:**
- `0`: Success
- `1032`: Request cancelled by user
- `1037`: Timeout
- `1`: Insufficient balance
- `2001`: Invalid phone number

---

#### B2C Result Callback
Receives Business to Customer (B2C) disbursement results.

```http
POST /webhooks/mpesa/b2c/result
Content-Type: application/json
```

**Request Body:**
```json
{
  "Result": {
    "ResultType": 0,
    "ResultCode": 0,
    "ResultDesc": "The service request is processed successfully.",
    "OriginatorConversationID": "10571-7910404-1",
    "ConversationID": "AG_20191219_00004e48cf7e3533f581",
    "TransactionID": "NLJ41HAY6Q",
    "ResultParameters": {
      "ResultParameter": [
        {"Key": "TransactionAmount", "Value": "5000.00"},
        {"Key": "TransactionReceipt", "Value": "NLJ41HAY6Q"},
        {"Key": "ReceiverPartyPublicName", "Value": "254708374149 - John Doe"},
        {"Key": "TransactionCompletedDateTime", "Value": "19.12.2019 11:45:50"},
        {"Key": "B2CUtilityAccountAvailableFunds", "Value": "10000.00"}
      ]
    }
  }
}
```

**Response:**
```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

---

#### C2B Confirmation
Receives Customer to Business (C2B) payment confirmations.

```http
POST /webhooks/mpesa/c2b/confirmation
Content-Type: application/json
```

**Request Body:**
```json
{
  "TransactionType": "Pay Bill",
  "TransID": "NLJ41HAY6Q",
  "TransTime": "20191219104905",
  "TransAmount": "1500.00",
  "BusinessShortCode": "600000",
  "BillRefNumber": "account123",
  "MSISDN": "254708374149",
  "FirstName": "John",
  "LastName": "Doe"
}
```

**Response:**
```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

---

### MTN Mobile Money Webhooks

#### Collection Callback
Receives MTN Mobile Money Collection (Request to Pay) results.

```http
POST /webhooks/mtn/collection
Content-Type: application/json
X-MTN-Signature: <signature>
```

**Request Body:**
```json
{
  "referenceId": "d4e90f52-7e4b-4f4a-9c3a-1234567890ab",
  "externalId": "ext_ref_123456",
  "status": "SUCCESSFUL",
  "amount": "1000.00",
  "currency": "UGX",
  "financialTransactionId": "12345678",
  "payer": {
    "partyIdType": "MSISDN",
    "partyId": "256774123456"
  },
  "payerMessage": "Payment for services",
  "payeeNote": "Order #12345"
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Callback received"
}
```

**Status Codes:**
- `PENDING`: Transaction is being processed
- `SUCCESSFUL`: Transaction completed successfully
- `FAILED`: Transaction failed

**Failure Reasons:**
- `PAYER_NOT_FOUND`: Payer account not found
- `PAYEE_NOT_FOUND`: Payee account not found
- `NOT_ALLOWED`: Transaction not allowed
- `NOT_ALLOWED_TARGET_ENVIRONMENT`: Target environment error
- `INVALID_CALLBACK_URL_HOST`: Invalid callback URL
- `INVALID_CURRENCY`: Currency not supported
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `INTERNAL_PROCESSING_ERROR`: Internal error
- `NOT_ENOUGH_FUNDS`: Insufficient balance
- `PAYER_LIMIT_REACHED`: Transaction limit exceeded
- `PAYEE_NOT_ALLOWED_TO_RECEIVE`: Payee cannot receive funds
- `PAYMENT_NOT_APPROVED`: Payment not approved by payer
- `RESOURCE_NOT_FOUND`: Resource not found
- `APPROVAL_REJECTED`: Payment rejected by payer
- `EXPIRED`: Transaction expired
- `TRANSACTION_CANCELED`: Transaction cancelled
- `RESOURCE_ALREADY_EXIST`: Duplicate transaction

---

#### Disbursement Callback
Receives MTN Mobile Money Disbursement (Transfer) results.

```http
POST /webhooks/mtn/disbursement
Content-Type: application/json
```

**Request Body:**
```json
{
  "referenceId": "transfer-456-xyz",
  "externalId": "ext_disb_001",
  "status": "SUCCESSFUL",
  "amount": "5000.00",
  "currency": "UGX",
  "financialTransactionId": "87654321",
  "payee": {
    "partyIdType": "MSISDN",
    "partyId": "256774123456"
  },
  "payerMessage": "Salary payment",
  "payeeNote": "Monthly salary"
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Callback received"
}
```

---

#### Remittance Callback
Receives MTN Mobile Money Remittance results.

```http
POST /webhooks/mtn/remittance
Content-Type: application/json
```

**Request Body:**
```json
{
  "referenceId": "remit-789-abc",
  "externalId": "ext_remit_001",
  "status": "SUCCESSFUL",
  "amount": "10000.00",
  "currency": "UGX",
  "financialTransactionId": "99887766",
  "payee": {
    "partyIdType": "MSISDN",
    "partyId": "256774123456"
  }
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Callback received"
}
```

---

### Airtel Money Webhooks

#### Payment Callback
Receives Airtel Money payment (push payment) results.

```http
POST /webhooks/airtel/payment
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction": {
    "id": "airtel_txn_123456789",
    "status": "TS",
    "message": "Transaction processed successfully"
  },
  "data": {
    "transaction": {
      "id": "merchant_ref_123456",
      "amount": "1000.00",
      "currency": "KES",
      "status": "TS",
      "message": "Success"
    }
  }
}
```

**Response:**
```json
{
  "status": {
    "code": "200",
    "message": "Callback received successfully",
    "success": true
  }
}
```

**Status Codes:**
- `TS`: Transaction Successful
- `TIP`: Transaction In Progress
- `TF`: Transaction Failed
- `TA`: Transaction Ambiguous
- `TU`: Transaction Unknown

**Error Codes:**
- `DP00800001007`: Insufficient Balance
- `DP00800001009`: Invalid MSISDN
- `DP00800001010`: Invalid Amount
- `DP00800001011`: Maximum transaction limit exceeded
- `DP00800001013`: Duplicate transaction
- `DP00800001014`: Transaction not found
- `DP00800001015`: Transaction expired
- `DP00800001016`: Subscriber not found
- `DP00800001017`: Invalid currency
- `DP00800001018`: Transaction declined
- `DP00800001019`: Service unavailable
- `DP00800001020`: System error

---

#### Disbursement Callback
Receives Airtel Money disbursement (payout) results.

```http
POST /webhooks/airtel/disbursement
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction": {
    "id": "airtel_disb_987654321",
    "status": "TS",
    "message": "Disbursement successful"
  },
  "data": {
    "transaction": {
      "id": "merchant_disb_789",
      "amount": "5000.00",
      "currency": "KES",
      "status": "TS"
    }
  }
}
```

**Response:**
```json
{
  "status": {
    "code": "200",
    "message": "Callback received successfully",
    "success": true
  }
}
```

---

#### Notification Callback
Receives general Airtel Money notifications.

```http
POST /webhooks/airtel/notification
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction": {
    "id": "notification_123",
    "status": "TS",
    "message": "General notification"
  }
}
```

**Response:**
```json
{
  "status": {
    "code": "200",
    "message": "Notification received",
    "success": true
  }
}
```

---

## Health Check Endpoints

### M-Pesa Health Check
```http
GET /webhooks/mpesa/health
```

**Response:**
```json
{
  "status": "healthy",
  "provider": "mpesa",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

### MTN Mobile Money Health Check
```http
GET /webhooks/mtn/health
```

**Response:**
```json
{
  "status": "healthy",
  "provider": "mtn_mobile_money",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

### Airtel Money Health Check
```http
GET /webhooks/airtel/health
```

**Response:**
```json
{
  "status": "healthy",
  "provider": "airtel_money",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## Webhook Best Practices

### 1. Immediate Acknowledgment
Always return a 200 OK response immediately to prevent provider retries:

```python
@router.post("/webhooks/mpesa/stkpush")
async def mpesa_callback(request: Request, background_tasks: BackgroundTasks):
    # Get callback data
    callback_data = await request.json()

    # Process in background
    background_tasks.add_task(process_callback, callback_data)

    # Return immediately
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
```

### 2. Idempotency
Handle duplicate callbacks gracefully:

```python
# Check if callback already processed
existing = await db.get_callback_by_reference(reference_id)
if existing and existing.processed:
    logger.info("Callback already processed", reference_id=reference_id)
    return {"status": "accepted"}  # Still return success
```

### 3. Signature Verification
Verify webhook signatures when provided:

```python
signature = request.headers.get("X-MTN-Signature")
if signature:
    is_valid = verify_signature(request.body, signature, secret_key)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid signature")
```

### 4. Error Handling
Log all errors but still return success:

```python
try:
    await process_callback(callback_data)
except Exception as e:
    logger.error("Callback processing failed", error=str(e))
    # Still return success to prevent retries
    return {"status": "accepted"}
```

### 5. Database Persistence
Store all callbacks for audit and reconciliation:

```python
callback = MMOCallback(
    provider="mpesa",
    provider_transaction_id=reference_id,
    callback_data=json.dumps(callback_data),
    callback_type="stk_push",
    status="successful",
    received_at=datetime.now(timezone.utc)
)
db.add(callback)
await db.commit()
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| All Webhook Endpoints | 1000 requests | per minute |
| Health Check Endpoints | 100 requests | per minute |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid callback data format",
  "code": "INVALID_FORMAT"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token",
  "code": "AUTH_REQUIRED"
}
```

### 429 Too Many Requests
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "code": "INTERNAL_ERROR",
  "request_id": "req_abc123"
}
```

---

## Testing Webhooks

### Using cURL

**M-Pesa STK Push Callback:**
```bash
curl -X POST http://localhost:8000/v1/webhooks/mpesa/stkpush \
  -H "Content-Type: application/json" \
  -d '{
    "Body": {
      "stkCallback": {
        "MerchantRequestID": "test-123",
        "CheckoutRequestID": "ws_CO_test",
        "ResultCode": 0,
        "ResultDesc": "Success"
      }
    }
  }'
```

**MTN Mobile Money Collection Callback:**
```bash
curl -X POST http://localhost:8000/v1/webhooks/mtn/collection \
  -H "Content-Type: application/json" \
  -d '{
    "referenceId": "test-ref-456",
    "status": "SUCCESSFUL",
    "amount": "1000.00",
    "currency": "UGX"
  }'
```

**Airtel Money Payment Callback:**
```bash
curl -X POST http://localhost:8000/v1/webhooks/airtel/payment \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "id": "test-airtel-789",
      "status": "TS",
      "message": "Success"
    }
  }'
```

### Using Test Fixtures

```python
from tests.fixtures import (
    MpesaCallbackFixtures,
    MTNMoMoCallbackFixtures,
    AirtelMoneyCallbackFixtures
)

# Get test callback data
mpesa_callback = MpesaCallbackFixtures.stk_push_success()
mtn_callback = MTNMoMoCallbackFixtures.collection_success()
airtel_callback = AirtelMoneyCallbackFixtures.payment_success()
```

---

## Support

For API support, contact:
- Email: api-support@capp.com
- Slack: #mmo-integration
- Documentation: https://docs.capp.com
