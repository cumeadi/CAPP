"""
Integration Tests for MTN Mobile Money Payment Operations

Tests MTN MoMo integration including:
- MTN MoMo Service (Collections, Disbursements, Remittances)
- OAuth2 Token Management
- Circuit Breaker Pattern
- Retry Logic with Exponential Backoff
- Webhook Endpoints
- Callback Processing
- Database Persistence

Prerequisites:
- PostgreSQL running on localhost:5432
- Database 'capp_test' created
- Alembic migrations run: alembic upgrade head

Run with: pytest tests/integration/test_mtn_momo_integration.py -v
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from httpx import AsyncClient, Response
import httpx

from fastapi import BackgroundTasks
from starlette.requests import Request

from applications.capp.capp.core.database import AsyncSessionLocal, Base, async_engine, MMOCallback
from applications.capp.capp.services.mtn_momo_integration import (
    MTNMoMoService, MTNMoMoProduct, MTNMoMoEnvironment
)
from applications.capp.capp.api.v1.endpoints import mtn_webhooks
from tests.fixtures.mtn_callbacks import MTNMoMoCallbackFixtures


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
def mtn_service(db_session):
    """Create MTN MoMo service instance"""
    return MTNMoMoService(db_session=db_session, environment="sandbox")


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for API calls"""
    return AsyncMock(spec=AsyncClient)


# =============================================================================
# MTN MoMo Service Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mtn_service_initialization(mtn_service):
    """Test MTN MoMo service initialization"""
    assert mtn_service is not None
    assert mtn_service.environment == MTNMoMoEnvironment.SANDBOX
    assert mtn_service.base_url == "https://sandbox.momodeveloper.mtn.com"
    assert MTNMoMoProduct.COLLECTION in mtn_service.circuit_breakers
    assert MTNMoMoProduct.DISBURSEMENT in mtn_service.circuit_breakers
    assert MTNMoMoProduct.REMITTANCE in mtn_service.circuit_breakers


@pytest.mark.asyncio
async def test_get_access_token_success(mtn_service, mock_httpx_client):
    """Test successful OAuth2 token retrieval"""
    # Mock successful token response
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "test_access_token_12345",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    mock_httpx_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        token = await mtn_service._get_access_token(MTNMoMoProduct.COLLECTION)

    assert token == "test_access_token_12345"
    assert MTNMoMoProduct.COLLECTION in mtn_service.access_tokens


@pytest.mark.asyncio
async def test_get_access_token_cached(mtn_service):
    """Test that cached tokens are returned"""
    # Pre-populate token cache
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    mtn_service.access_tokens[MTNMoMoProduct.COLLECTION] = {
        "access_token": "cached_token_xyz",
        "expires_at": future_time
    }

    token = await mtn_service._get_access_token(MTNMoMoProduct.COLLECTION)

    assert token == "cached_token_xyz"


@pytest.mark.asyncio
async def test_get_access_token_expired_refresh(mtn_service, mock_httpx_client):
    """Test token refresh when cached token expires"""
    # Pre-populate with expired token
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    mtn_service.access_tokens[MTNMoMoProduct.COLLECTION] = {
        "access_token": "expired_token",
        "expires_at": past_time
    }

    # Mock new token response
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_token_abc",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    mock_httpx_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        token = await mtn_service._get_access_token(MTNMoMoProduct.COLLECTION)

    assert token == "new_token_abc"
    assert mtn_service.access_tokens[MTNMoMoProduct.COLLECTION]["access_token"] == "new_token_abc"


@pytest.mark.asyncio
async def test_request_to_pay_success(mtn_service, mock_httpx_client):
    """Test successful Request to Pay (Collection)"""
    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock successful payment request
        mock_response = Mock(spec=Response)
        mock_response.status_code = 202
        mock_response.headers = {"X-Reference-Id": "test-ref-123"}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.request_to_pay(
                phone_number="256774123456",
                amount=1000.0,
                currency="UGX",
                external_id="ext_ref_001",
                payer_message="Test payment",
                payee_note="Payment for services"
            )

    assert result["success"] is True
    assert "reference_id" in result
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_request_to_pay_circuit_breaker_open(mtn_service):
    """Test Request to Pay when circuit breaker is open"""
    # Open the circuit breaker
    circuit_breaker = mtn_service.circuit_breakers[MTNMoMoProduct.COLLECTION]
    circuit_breaker.state = "OPEN"

    result = await mtn_service.request_to_pay(
        phone_number="256774123456",
        amount=1000.0,
        currency="UGX",
        external_id="ext_ref_002",
        payer_message="Test payment",
        payee_note="Payment for services"
    )

    assert result["success"] is False
    assert "circuit breaker is open" in result["message"].lower()


@pytest.mark.asyncio
async def test_transfer_success(mtn_service, mock_httpx_client):
    """Test successful Transfer (Disbursement)"""
    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock successful transfer request
        mock_response = Mock(spec=Response)
        mock_response.status_code = 202
        mock_response.headers = {"X-Reference-Id": "transfer-ref-456"}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.transfer(
                phone_number="256774123456",
                amount=5000.0,
                currency="UGX",
                external_id="ext_transfer_001",
                payee_note="Disbursement payment",
                payer_message="Payment sent"
            )

    assert result["success"] is True
    assert "reference_id" in result
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_get_transaction_status_success(mtn_service, mock_httpx_client):
    """Test successful transaction status query"""
    reference_id = "test-ref-789"

    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock status response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "referenceId": reference_id,
            "status": "SUCCESSFUL",
            "amount": "1000.00",
            "currency": "UGX",
            "financialTransactionId": "12345678",
            "externalId": "ext_ref_001",
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": "256774123456"
            }
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.get_transaction_status(
                reference_id=reference_id,
                product=MTNMoMoProduct.COLLECTION
            )

    assert result["success"] is True
    assert result["status"] == "SUCCESSFUL"
    assert result["amount"] == "1000.00"


@pytest.mark.asyncio
async def test_get_transaction_status_pending(mtn_service, mock_httpx_client):
    """Test transaction status query for pending transaction"""
    reference_id = "test-ref-pending"

    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock pending status response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "referenceId": reference_id,
            "status": "PENDING",
            "amount": "1000.00",
            "currency": "UGX"
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.get_transaction_status(
                reference_id=reference_id,
                product=MTNMoMoProduct.COLLECTION
            )

    assert result["success"] is True
    assert result["status"] == "PENDING"


@pytest.mark.asyncio
async def test_get_transaction_status_failed(mtn_service, mock_httpx_client):
    """Test transaction status query for failed transaction"""
    reference_id = "test-ref-failed"

    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock failed status response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "referenceId": reference_id,
            "status": "FAILED",
            "amount": "1000.00",
            "currency": "UGX",
            "reason": "PAYER_NOT_FOUND"
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.get_transaction_status(
                reference_id=reference_id,
                product=MTNMoMoProduct.COLLECTION
            )

    assert result["success"] is False
    assert result["status"] == "FAILED"
    assert result["reason"] == "PAYER_NOT_FOUND"


# =============================================================================
# Webhook Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_collection_callback_success(db_session):
    """Test Collection callback with successful transaction"""
    callback_data = MTNMoMoCallbackFixtures.collection_success()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {"X-MTN-Signature": "test_signature"}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await mtn_webhooks.mtn_collection_callback(request, background_tasks, db_session)

    assert response.status_code == 200
    response_data = json.loads(response.body.decode())
    assert response_data["status"] == "accepted"


@pytest.mark.asyncio
async def test_collection_callback_failed(db_session):
    """Test Collection callback with failed transaction"""
    callback_data = MTNMoMoCallbackFixtures.collection_failed()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {"X-MTN-Signature": "test_signature"}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await mtn_webhooks.mtn_collection_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_disbursement_callback_success(db_session):
    """Test Disbursement callback with successful transaction"""
    callback_data = MTNMoMoCallbackFixtures.disbursement_success()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await mtn_webhooks.mtn_disbursement_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_remittance_callback_success(db_session):
    """Test Remittance callback"""
    callback_data = MTNMoMoCallbackFixtures.remittance_success()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await mtn_webhooks.mtn_remittance_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_callback_processing_database_persistence(db_session):
    """Test that callbacks are persisted to database"""
    callback_data = MTNMoMoCallbackFixtures.collection_success()

    # Process callback directly
    await mtn_webhooks.process_collection_callback(callback_data, db_session)

    # Query database for callback
    from sqlalchemy import select
    result = await db_session.execute(
        select(MMOCallback).where(
            MMOCallback.provider == "mtn_mobile_money",
            MMOCallback.provider_transaction_id == callback_data["referenceId"]
        )
    )
    callback = result.scalar_one_or_none()

    assert callback is not None
    assert callback.callback_type == "collection"
    assert callback.status == "successful"
    assert float(callback.amount) == 1000.0
    assert callback.currency == "UGX"


# =============================================================================
# Circuit Breaker Tests
# =============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(mtn_service, mock_httpx_client):
    """Test circuit breaker opens after consecutive failures"""
    circuit_breaker = mtn_service.circuit_breakers[MTNMoMoProduct.COLLECTION]
    circuit_breaker.reset()  # Start with closed circuit

    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock failed responses
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            # Trigger failures to open circuit breaker
            for i in range(6):  # Threshold is 5
                try:
                    await mtn_service.request_to_pay(
                        phone_number="256774123456",
                        amount=1000.0,
                        currency="UGX",
                        external_id=f"ext_ref_{i}",
                        payer_message="Test",
                        payee_note="Test"
                    )
                except Exception:
                    pass

    # Circuit breaker should be open now
    assert circuit_breaker.state == "OPEN"


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery(mtn_service, mock_httpx_client):
    """Test circuit breaker transitions to half-open and recovers"""
    circuit_breaker = mtn_service.circuit_breakers[MTNMoMoProduct.COLLECTION]

    # Set circuit to open and expired timeout
    circuit_breaker.state = "OPEN"
    circuit_breaker.opened_at = datetime.now(timezone.utc) - timedelta(seconds=61)

    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # Mock successful response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 202
        mock_response.headers = {"X-Reference-Id": "recovery-ref"}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.request_to_pay(
                phone_number="256774123456",
                amount=1000.0,
                currency="UGX",
                external_id="recovery_ref",
                payer_message="Recovery test",
                payee_note="Test"
            )

    # Circuit should be closed again
    assert result["success"] is True
    assert circuit_breaker.state == "CLOSED"


# =============================================================================
# Retry Logic Tests
# =============================================================================

@pytest.mark.asyncio
async def test_retry_logic_on_network_failure(mtn_service, mock_httpx_client):
    """Test retry logic with exponential backoff on network failures"""
    call_count = 0

    async def mock_post_with_retry(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.RequestError("Network error", request=None)
        # Success on third attempt
        mock_response = Mock(spec=Response)
        mock_response.status_code = 202
        mock_response.headers = {"X-Reference-Id": "retry-ref"}
        return mock_response

    # Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        mock_httpx_client.post = mock_post_with_retry

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.request_to_pay(
                phone_number="256774123456",
                amount=1000.0,
                currency="UGX",
                external_id="retry_test",
                payer_message="Retry test",
                payee_note="Test"
            )

    # Should succeed after retries
    assert result["success"] is True
    assert call_count == 3  # Failed twice, succeeded on third


# =============================================================================
# Integration Tests - Full Flow
# =============================================================================

@pytest.mark.asyncio
async def test_complete_collection_flow(db_session, mock_httpx_client):
    """Test complete Collection flow from initiation to callback"""
    mtn_service = MTNMoMoService(db_session=db_session, environment="sandbox")

    # 1. Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # 2. Initiate Request to Pay
        mock_response = Mock(spec=Response)
        mock_response.status_code = 202
        reference_id = str(uuid4())
        mock_response.headers = {"X-Reference-Id": reference_id}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.request_to_pay(
                phone_number="256774123456",
                amount=1000.0,
                currency="UGX",
                external_id="complete_flow_test",
                payer_message="Test payment",
                payee_note="Payment for services"
            )

    assert result["success"] is True
    assert result["status"] == "pending"

    # 3. Process callback (simulate MTN response)
    callback_data = MTNMoMoCallbackFixtures.collection_success()
    callback_data["referenceId"] = reference_id

    await mtn_webhooks.process_collection_callback(callback_data, db_session)

    # 4. Verify callback stored in database
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(MMOCallback).where(
            MMOCallback.provider == "mtn_mobile_money",
            MMOCallback.provider_transaction_id == reference_id
        )
    )
    callback = db_result.scalar_one_or_none()

    assert callback is not None
    assert callback.status == "successful"
    assert callback.callback_type == "collection"


@pytest.mark.asyncio
async def test_complete_disbursement_flow(db_session, mock_httpx_client):
    """Test complete Disbursement flow"""
    mtn_service = MTNMoMoService(db_session=db_session, environment="sandbox")

    # 1. Mock access token
    with patch.object(mtn_service, '_get_access_token', return_value="test_token"):
        # 2. Initiate Transfer
        mock_response = Mock(spec=Response)
        mock_response.status_code = 202
        reference_id = str(uuid4())
        mock_response.headers = {"X-Reference-Id": reference_id}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await mtn_service.transfer(
                phone_number="256774123456",
                amount=5000.0,
                currency="UGX",
                external_id="disbursement_flow_test",
                payee_note="Disbursement payment",
                payer_message="Payment sent"
            )

    assert result["success"] is True

    # 3. Process callback
    callback_data = MTNMoMoCallbackFixtures.disbursement_success()
    callback_data["referenceId"] = reference_id

    await mtn_webhooks.process_disbursement_callback(callback_data, db_session)

    # 4. Verify callback
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(MMOCallback).where(
            MMOCallback.provider == "mtn_mobile_money",
            MMOCallback.provider_transaction_id == reference_id
        )
    )
    callback = db_result.scalar_one_or_none()

    assert callback is not None
    assert callback.callback_type == "disbursement"


@pytest.mark.asyncio
async def test_webhook_health_endpoint():
    """Test MTN webhook health check endpoint"""
    response = await mtn_webhooks.mtn_webhook_health()

    assert response["status"] == "healthy"
    assert response["provider"] == "mtn_mobile_money"


if __name__ == "__main__":
    print("Run with: pytest tests/integration/test_mtn_momo_integration.py -v")
