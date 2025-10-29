"""
Integration Tests for M-Pesa Payment Operations

Tests M-Pesa integration including:
- M-Pesa Transaction Repository
- M-Pesa Webhook Endpoints
- Callback Processing
- Database Persistence
- Error Handling

Prerequisites:
- PostgreSQL running on localhost:5432
- Database 'capp_test' created
- Alembic migrations run: alembic upgrade head

Run with: pytest tests/integration/test_mpesa_integration.py -v
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from fastapi import BackgroundTasks
from starlette.requests import Request
from httpx import AsyncClient

from applications.capp.capp.core.database import AsyncSessionLocal, Base, async_engine
from applications.capp.capp.repositories.mpesa import MpesaRepository
from applications.capp.capp.repositories.payment import PaymentRepository
from applications.capp.capp.api.v1.endpoints import webhooks


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def setup_database():
    """Set up test database"""
    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Create database session for tests"""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def sample_stk_push_callback():
    """Sample M-Pesa STK Push callback data"""
    return {
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


@pytest.fixture
def sample_stk_push_failed_callback():
    """Sample M-Pesa STK Push failed callback"""
    return {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-2",
                "CheckoutRequestID": "ws_CO_191220191020363926",
                "ResultCode": 1032,
                "ResultDesc": "Request cancelled by user"
            }
        }
    }


@pytest.fixture
def sample_b2c_result_callback():
    """Sample M-Pesa B2C result callback"""
    return {
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
                    {"Key": "B2CUtilityAccountAvailableFunds", "Value": "10000.00"},
                    {"Key": "B2CWorkingAccountAvailableFunds", "Value": "900000.00"},
                    {"Key": "B2CRecipientIsRegisteredCustomer", "Value": "Y"}
                ]
            },
            "ReferenceData": {
                "ReferenceItem": {
                    "Key": "QueueTimeoutURL",
                    "Value": "https://internalsandbox.safaricom.co.ke/mpesa/b2cresults/v1/submit"
                }
            }
        }
    }


@pytest.fixture
def sample_c2b_confirmation():
    """Sample M-Pesa C2B confirmation"""
    return {
        "TransactionType": "Pay Bill",
        "TransID": "NLJ41HAY6Q",
        "TransTime": "20191219104905",
        "TransAmount": "1500.00",
        "BusinessShortCode": "600000",
        "BillRefNumber": "account123",
        "InvoiceNumber": "",
        "OrgAccountBalance": "49001.00",
        "ThirdPartyTransID": "",
        "MSISDN": "254708374149",
        "FirstName": "John",
        "MiddleName": "",
        "LastName": "Doe"
    }


# =============================================================================
# M-Pesa Repository Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_mpesa_transaction(db_session):
    """Test creating M-Pesa transaction"""
    repo = MpesaRepository(db_session)

    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id="ws_CO_191220191020363925",
        merchant_request_id="29115-34620561-1",
        account_reference="TEST001",
        transaction_desc="Test payment"
    )

    assert transaction.id is not None
    assert transaction.transaction_type == "stk_push"
    assert transaction.phone_number == "254708374149"
    assert transaction.amount == Decimal("1000.00")
    assert transaction.status == "pending"
    assert transaction.checkout_request_id == "ws_CO_191220191020363925"
    assert transaction.retry_count == 0


@pytest.mark.asyncio
async def test_get_transaction_by_checkout_request_id(db_session):
    """Test retrieving transaction by checkout request ID"""
    repo = MpesaRepository(db_session)

    # Create transaction
    checkout_request_id = f"ws_CO_{uuid4().hex[:20]}"
    await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("500.00"),
        checkout_request_id=checkout_request_id
    )

    # Retrieve it
    transaction = await repo.get_by_checkout_request_id(checkout_request_id)

    assert transaction is not None
    assert transaction.checkout_request_id == checkout_request_id
    assert transaction.amount == Decimal("500.00")


@pytest.mark.asyncio
async def test_update_mpesa_transaction(db_session):
    """Test updating M-Pesa transaction"""
    repo = MpesaRepository(db_session)

    # Create transaction
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id=f"ws_CO_{uuid4().hex[:20]}"
    )

    # Update it
    updated = await repo.update_transaction(
        transaction_id=transaction.id,
        status="completed",
        result_code=0,
        result_description="Success",
        mpesa_receipt_number="NLJ7RT61SV",
        transaction_date=datetime.utcnow()
    )

    assert updated is not None
    assert updated.status == "completed"
    assert updated.result_code == 0
    assert updated.mpesa_receipt_number == "NLJ7RT61SV"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_create_mpesa_callback(db_session):
    """Test creating M-Pesa callback record"""
    repo = MpesaRepository(db_session)

    # Create transaction first
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id=f"ws_CO_{uuid4().hex[:20]}"
    )

    # Create callback
    callback = await repo.create_callback(
        callback_type="stk_push",
        callback_data={"test": "data"},
        checkout_request_id=transaction.checkout_request_id,
        mpesa_transaction_id=transaction.id
    )

    assert callback.id is not None
    assert callback.callback_type == "stk_push"
    assert callback.mpesa_transaction_id == transaction.id
    assert callback.processed is False
    assert callback.processing_attempts == 0


@pytest.mark.asyncio
async def test_mark_callback_processed(db_session):
    """Test marking callback as processed"""
    repo = MpesaRepository(db_session)

    # Create transaction and callback
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00")
    )

    callback = await repo.create_callback(
        callback_type="stk_push",
        callback_data={"test": "data"},
        mpesa_transaction_id=transaction.id
    )

    # Mark as processed
    updated = await repo.mark_callback_processed(
        callback_id=callback.id,
        success=True
    )

    assert updated is not None
    assert updated.processed is True
    assert updated.processed_at is not None
    assert updated.processing_attempts == 1


@pytest.mark.asyncio
async def test_get_pending_transactions(db_session):
    """Test retrieving pending transactions"""
    repo = MpesaRepository(db_session)

    # Create old pending transaction
    old_transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00")
    )

    # Manually set created_at to 10 minutes ago
    old_transaction.created_at = datetime.utcnow() - timedelta(minutes=10)
    await db_session.commit()

    # Create recent pending transaction
    await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374150",
        amount=Decimal("500.00")
    )

    # Get pending transactions older than 5 minutes
    pending = await repo.get_pending_transactions(minutes_old=5)

    assert len(pending) >= 1
    assert any(t.id == old_transaction.id for t in pending)


@pytest.mark.asyncio
async def test_get_transaction_statistics(db_session):
    """Test transaction statistics"""
    repo = MpesaRepository(db_session)

    # Create multiple transactions with different statuses
    for i in range(10):
        status = "completed" if i < 7 else "failed"
        await repo.create_transaction(
            transaction_type="stk_push",
            phone_number=f"25470837414{i}",
            amount=Decimal("1000.00")
        )
        # Update status
        transaction = await repo.get_by_phone_number(f"25470837414{i}")
        if transaction:
            await repo.update_transaction(
                transaction_id=transaction[0].id,
                status=status
            )

    # Get statistics
    stats = await repo.get_transaction_statistics(
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow()
    )

    assert stats["total_transactions"] >= 10
    assert stats["success_rate"] > 0


@pytest.mark.asyncio
async def test_get_by_receipt_number(db_session):
    """Test retrieving transaction by M-Pesa receipt number"""
    repo = MpesaRepository(db_session)

    # Create transaction with receipt
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00")
    )

    receipt_number = "NLJ7RT61SV"
    await repo.update_transaction(
        transaction_id=transaction.id,
        mpesa_receipt_number=receipt_number
    )

    # Retrieve by receipt
    found = await repo.get_by_receipt_number(receipt_number)

    assert found is not None
    assert found.id == transaction.id
    assert found.mpesa_receipt_number == receipt_number


@pytest.mark.asyncio
async def test_increment_retry_count(db_session):
    """Test incrementing retry count"""
    repo = MpesaRepository(db_session)

    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00")
    )

    # Increment retry count
    updated = await repo.increment_retry_count(transaction.id)

    assert updated.retry_count == 1
    assert updated.last_retry_at is not None


@pytest.mark.asyncio
async def test_get_unprocessed_callbacks(db_session):
    """Test retrieving unprocessed callbacks"""
    repo = MpesaRepository(db_session)

    # Create transaction and callbacks
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00")
    )

    # Create unprocessed callback
    await repo.create_callback(
        callback_type="stk_push",
        callback_data={"test": "data1"},
        mpesa_transaction_id=transaction.id
    )

    # Create processed callback
    callback2 = await repo.create_callback(
        callback_type="stk_push",
        callback_data={"test": "data2"},
        mpesa_transaction_id=transaction.id
    )
    await repo.mark_callback_processed(callback2.id, success=True)

    # Get unprocessed
    unprocessed = await repo.get_unprocessed_callbacks(limit=10)

    assert len(unprocessed) >= 1
    assert all(not c.processed for c in unprocessed)


# =============================================================================
# Webhook Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_stk_push_callback_success(db_session, sample_stk_push_callback):
    """Test STK Push callback with successful transaction"""
    repo = MpesaRepository(db_session)

    # Create pending transaction
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id="ws_CO_191220191020363925",
        merchant_request_id="29115-34620561-1"
    )

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(sample_stk_push_callback).encode())
    request.headers = {"X-Mpesa-Signature": "test_signature"}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await webhooks.mpesa_stk_push_callback(request, background_tasks, db_session)

    assert response.status_code == 200
    assert response.body == b'{"ResultCode":0,"ResultDesc":"Accepted"}'


@pytest.mark.asyncio
async def test_stk_push_callback_failed(db_session, sample_stk_push_failed_callback):
    """Test STK Push callback with failed transaction"""
    repo = MpesaRepository(db_session)

    # Create pending transaction
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id="ws_CO_191220191020363926",
        merchant_request_id="29115-34620561-2"
    )

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(sample_stk_push_failed_callback).encode())
    request.headers = {"X-Mpesa-Signature": "test_signature"}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await webhooks.mpesa_stk_push_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_b2c_result_callback(db_session, sample_b2c_result_callback):
    """Test B2C result callback"""
    repo = MpesaRepository(db_session)

    # Create pending B2C transaction
    transaction = await repo.create_transaction(
        transaction_type="b2c",
        phone_number="254708374149",
        amount=Decimal("5000.00"),
        conversation_id="AG_20191219_00004e48cf7e3533f581"
    )

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(sample_b2c_result_callback).encode())
    request.headers = {"X-Mpesa-Signature": "test_signature"}

    # Process callback
    response = await webhooks.mpesa_b2c_result_callback(request, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_c2b_confirmation(db_session, sample_c2b_confirmation):
    """Test C2B confirmation callback"""
    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(sample_c2b_confirmation).encode())
    request.headers = {}

    # Process callback
    response = await webhooks.mpesa_c2b_confirmation(request, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_timeout_callback(db_session):
    """Test M-Pesa timeout callback"""
    repo = MpesaRepository(db_session)

    # Create pending transaction
    transaction = await repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id="ws_CO_timeout123"
    )

    timeout_data = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": "ws_CO_timeout123",
                "ResultCode": 1,
                "ResultDesc": "Request timeout"
            }
        }
    }

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(timeout_data).encode())
    request.headers = {}

    # Process callback
    response = await webhooks.mpesa_timeout_callback(request, db_session)

    assert response.status_code == 200


# =============================================================================
# Integration Tests - Full Flow
# =============================================================================

@pytest.mark.asyncio
async def test_complete_stk_push_flow(db_session, sample_stk_push_callback):
    """Test complete STK Push flow from initiation to callback"""
    mpesa_repo = MpesaRepository(db_session)

    # 1. Create M-Pesa transaction
    transaction = await mpesa_repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id="ws_CO_191220191020363925",
        merchant_request_id="29115-34620561-1",
        account_reference="TEST_PAYMENT_001",
        transaction_desc="Test payment",
        request_payload={"test": "data"}
    )

    assert transaction.status == "pending"

    # 2. Process callback (simulate M-Pesa response)
    await webhooks.process_stk_push_callback(
        sample_stk_push_callback,
        db_session
    )

    # 3. Verify transaction updated
    updated_transaction = await mpesa_repo.get_by_checkout_request_id(
        "ws_CO_191220191020363925"
    )

    assert updated_transaction.status == "completed"
    assert updated_transaction.result_code == 0
    assert updated_transaction.mpesa_receipt_number == "NLJ7RT61SV"
    assert updated_transaction.completed_at is not None

    # 4. Verify callback recorded
    callbacks = await mpesa_repo.get_callbacks_by_transaction(transaction.id)
    assert len(callbacks) >= 1
    assert callbacks[0].callback_type == "stk_push"


@pytest.mark.asyncio
async def test_complete_b2c_flow(db_session, sample_b2c_result_callback):
    """Test complete B2C flow"""
    mpesa_repo = MpesaRepository(db_session)

    # 1. Create B2C transaction
    transaction = await mpesa_repo.create_transaction(
        transaction_type="b2c",
        phone_number="254708374149",
        amount=Decimal("5000.00"),
        conversation_id="AG_20191219_00004e48cf7e3533f581",
        transaction_desc="B2C disbursement"
    )

    assert transaction.status == "pending"

    # 2. Process B2C result callback
    await webhooks.process_b2c_result_callback(
        sample_b2c_result_callback,
        db_session
    )

    # 3. Verify transaction updated
    updated_transaction = await mpesa_repo.get_by_conversation_id(
        "AG_20191219_00004e48cf7e3533f581"
    )

    assert updated_transaction.status == "completed"
    assert updated_transaction.mpesa_receipt_number == "NLJ41HAY6Q"


if __name__ == "__main__":
    print("Run with: pytest tests/integration/test_mpesa_integration.py -v")
