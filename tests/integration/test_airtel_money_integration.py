"""
Integration Tests for Airtel Money Payment Operations

Tests Airtel Money integration including:
- Airtel Money Service (Push Payment, Disbursement)
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

Run with: pytest tests/integration/test_airtel_money_integration.py -v
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

from applications.capp.capp.core.database import AsyncSessionLocal, Base, engine, MMOCallback
from applications.capp.capp.services.airtel_money_integration import AirtelMoneyService
from applications.capp.capp.api.v1.endpoints import airtel_webhooks
from tests.fixtures.airtel_callbacks import AirtelMoneyCallbackFixtures


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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Create database session for tests"""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def airtel_service(db_session):
    """Create Airtel Money service instance"""
    return AirtelMoneyService(db_session=db_session, environment="staging")


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for API calls"""
    return AsyncMock(spec=AsyncClient)


# =============================================================================
# Airtel Money Service Tests
# =============================================================================

@pytest.mark.asyncio
async def test_airtel_service_initialization(airtel_service):
    """Test Airtel Money service initialization"""
    assert airtel_service is not None
    assert airtel_service.environment == "staging"
    assert airtel_service.base_url == "https://openapiuat.airtel.africa"
    assert airtel_service.circuit_breaker is not None


@pytest.mark.asyncio
async def test_get_access_token_success(airtel_service, mock_httpx_client):
    """Test successful OAuth2 token retrieval"""
    # Mock successful token response
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "airtel_test_token_xyz",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    mock_httpx_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        token = await airtel_service._get_access_token()

    assert token == "airtel_test_token_xyz"
    assert airtel_service.access_token == "airtel_test_token_xyz"


@pytest.mark.asyncio
async def test_get_access_token_cached(airtel_service):
    """Test that cached tokens are returned"""
    # Pre-populate token cache
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    airtel_service.access_token = "cached_airtel_token"
    airtel_service.token_expires_at = future_time

    token = await airtel_service._get_access_token()

    assert token == "cached_airtel_token"


@pytest.mark.asyncio
async def test_get_access_token_expired_refresh(airtel_service, mock_httpx_client):
    """Test token refresh when cached token expires"""
    # Pre-populate with expired token
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    airtel_service.access_token = "expired_airtel_token"
    airtel_service.token_expires_at = past_time

    # Mock new token response
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_airtel_token_123",
        "token_type": "Bearer",
        "expires_in": 3600
    }
    mock_httpx_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        token = await airtel_service._get_access_token()

    assert token == "new_airtel_token_123"
    assert airtel_service.access_token == "new_airtel_token_123"


@pytest.mark.asyncio
async def test_push_payment_success(airtel_service, mock_httpx_client):
    """Test successful Push Payment"""
    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock successful payment response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "airtel_txn_123456",
                    "status": "TIP"  # Transaction In Progress
                }
            },
            "status": {
                "code": "200",
                "message": "Transaction initiated successfully",
                "success": True
            }
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.push_payment(
                phone_number="254700123456",
                amount=1000.0,
                currency="KES",
                transaction_id="test_push_001",
                country_code="KE"
            )

    assert result["success"] is True
    assert "transaction_id" in result
    assert result["status"] == "TIP"


@pytest.mark.asyncio
async def test_push_payment_circuit_breaker_open(airtel_service):
    """Test Push Payment when circuit breaker is open"""
    # Open the circuit breaker
    airtel_service.circuit_breaker.state = "OPEN"

    result = await airtel_service.push_payment(
        phone_number="254700123456",
        amount=1000.0,
        currency="KES",
        transaction_id="test_push_002",
        country_code="KE"
    )

    assert result["success"] is False
    assert "circuit breaker is open" in result["message"].lower()


@pytest.mark.asyncio
async def test_disbursement_success(airtel_service, mock_httpx_client):
    """Test successful Disbursement"""
    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock successful disbursement response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "airtel_disb_789",
                    "status": "TS"  # Transaction Successful
                }
            },
            "status": {
                "code": "200",
                "message": "Disbursement successful",
                "success": True
            }
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.disbursement(
                phone_number="254700123456",
                amount=5000.0,
                currency="KES",
                transaction_id="test_disb_001",
                country_code="KE"
            )

    assert result["success"] is True
    assert "transaction_id" in result
    assert result["status"] == "TS"


@pytest.mark.asyncio
async def test_disbursement_failed(airtel_service, mock_httpx_client):
    """Test failed Disbursement"""
    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock failed disbursement response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "airtel_disb_fail",
                    "status": "TF"  # Transaction Failed
                }
            },
            "status": {
                "code": "DP00800001007",
                "message": "Insufficient Balance",
                "success": False
            }
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.disbursement(
                phone_number="254700123456",
                amount=50000.0,
                currency="KES",
                transaction_id="test_disb_fail",
                country_code="KE"
            )

    assert result["success"] is False
    assert result["status"] == "TF"


@pytest.mark.asyncio
async def test_get_transaction_status_success(airtel_service, mock_httpx_client):
    """Test successful transaction status query"""
    transaction_id = "airtel_status_test_123"

    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock status response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": transaction_id,
                    "status": "TS",
                    "amount": "1000.00",
                    "currency": "KES"
                }
            },
            "status": {
                "code": "200",
                "message": "Transaction successful",
                "success": True
            }
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.get_transaction_status(
                transaction_id=transaction_id,
                country_code="KE"
            )

    assert result["success"] is True
    assert result["status"] == "TS"


@pytest.mark.asyncio
async def test_get_transaction_status_pending(airtel_service, mock_httpx_client):
    """Test transaction status query for pending transaction"""
    transaction_id = "airtel_pending_123"

    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock pending status response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": transaction_id,
                    "status": "TIP",
                    "amount": "1000.00",
                    "currency": "KES"
                }
            }
        }
        mock_httpx_client.get = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.get_transaction_status(
                transaction_id=transaction_id,
                country_code="KE"
            )

    assert result["success"] is True
    assert result["status"] == "TIP"


# =============================================================================
# Webhook Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_payment_callback_success(db_session):
    """Test Payment callback with successful transaction"""
    callback_data = AirtelMoneyCallbackFixtures.payment_success()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await airtel_webhooks.airtel_payment_callback(request, background_tasks, db_session)

    assert response.status_code == 200
    response_data = json.loads(response.body.decode())
    assert response_data["status"]["success"] is True


@pytest.mark.asyncio
async def test_payment_callback_failed(db_session):
    """Test Payment callback with failed transaction"""
    callback_data = AirtelMoneyCallbackFixtures.payment_failed()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await airtel_webhooks.airtel_payment_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_payment_callback_pending(db_session):
    """Test Payment callback with pending transaction"""
    callback_data = AirtelMoneyCallbackFixtures.payment_pending()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await airtel_webhooks.airtel_payment_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_disbursement_callback_success(db_session):
    """Test Disbursement callback with successful transaction"""
    callback_data = AirtelMoneyCallbackFixtures.disbursement_success()

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await airtel_webhooks.airtel_disbursement_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_notification_callback(db_session):
    """Test general notification callback"""
    callback_data = {
        "transaction": {
            "id": "notification_test_123",
            "status": "TS",
            "message": "General notification"
        }
    }

    # Mock request
    request = Mock(spec=Request)
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())
    request.headers = {}

    # Process callback
    background_tasks = BackgroundTasks()
    response = await airtel_webhooks.airtel_notification_callback(request, background_tasks, db_session)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_callback_processing_database_persistence(db_session):
    """Test that callbacks are persisted to database"""
    callback_data = AirtelMoneyCallbackFixtures.payment_success()

    # Process callback directly
    await airtel_webhooks.process_payment_callback(callback_data, db_session)

    # Query database for callback
    from sqlalchemy import select
    result = await db_session.execute(
        select(MMOCallback).where(
            MMOCallback.provider == "airtel_money",
            MMOCallback.provider_transaction_id == callback_data["transaction"]["id"]
        )
    )
    callback = result.scalar_one_or_none()

    assert callback is not None
    assert callback.callback_type == "payment"
    assert callback.status == "successful"


# =============================================================================
# Circuit Breaker Tests
# =============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(airtel_service, mock_httpx_client):
    """Test circuit breaker opens after consecutive failures"""
    airtel_service.circuit_breaker.reset()  # Start with closed circuit

    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock failed responses
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            # Trigger failures to open circuit breaker
            for i in range(6):  # Threshold is 5
                try:
                    await airtel_service.push_payment(
                        phone_number="254700123456",
                        amount=1000.0,
                        currency="KES",
                        transaction_id=f"fail_test_{i}",
                        country_code="KE"
                    )
                except Exception:
                    pass

    # Circuit breaker should be open now
    assert airtel_service.circuit_breaker.state == "OPEN"


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery(airtel_service, mock_httpx_client):
    """Test circuit breaker transitions to half-open and recovers"""
    # Set circuit to open and expired timeout
    airtel_service.circuit_breaker.state = "OPEN"
    airtel_service.circuit_breaker.opened_at = datetime.now(timezone.utc) - timedelta(seconds=61)

    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # Mock successful response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "recovery_test",
                    "status": "TS"
                }
            },
            "status": {
                "code": "200",
                "success": True
            }
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.push_payment(
                phone_number="254700123456",
                amount=1000.0,
                currency="KES",
                transaction_id="recovery_test",
                country_code="KE"
            )

    # Circuit should be closed again
    assert result["success"] is True
    assert airtel_service.circuit_breaker.state == "CLOSED"


# =============================================================================
# Retry Logic Tests
# =============================================================================

@pytest.mark.asyncio
async def test_retry_logic_on_network_failure(airtel_service, mock_httpx_client):
    """Test retry logic with exponential backoff on network failures"""
    call_count = 0

    async def mock_post_with_retry(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.RequestError("Network error", request=None)
        # Success on third attempt
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": "retry_test",
                    "status": "TS"
                }
            },
            "status": {"code": "200", "success": True}
        }
        return mock_response

    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        mock_httpx_client.post = mock_post_with_retry

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.push_payment(
                phone_number="254700123456",
                amount=1000.0,
                currency="KES",
                transaction_id="retry_test",
                country_code="KE"
            )

    # Should succeed after retries
    assert result["success"] is True
    assert call_count == 3  # Failed twice, succeeded on third


@pytest.mark.asyncio
async def test_retry_logic_max_attempts(airtel_service, mock_httpx_client):
    """Test retry logic gives up after max attempts"""
    call_count = 0

    async def mock_post_always_fail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise httpx.RequestError("Network error", request=None)

    # Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        mock_httpx_client.post = mock_post_always_fail

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.push_payment(
                phone_number="254700123456",
                amount=1000.0,
                currency="KES",
                transaction_id="max_retry_test",
                country_code="KE"
            )

    # Should fail after max retries
    assert result["success"] is False
    assert call_count == 3  # Initial + 2 retries = 3 attempts


# =============================================================================
# Status Code Mapping Tests
# =============================================================================

@pytest.mark.asyncio
async def test_status_code_mapping_ts():
    """Test TS (Transaction Successful) status mapping"""
    callback_data = AirtelMoneyCallbackFixtures.payment_success()
    assert callback_data["transaction"]["status"] == "TS"


@pytest.mark.asyncio
async def test_status_code_mapping_tip():
    """Test TIP (Transaction In Progress) status mapping"""
    callback_data = AirtelMoneyCallbackFixtures.payment_pending()
    assert callback_data["transaction"]["status"] == "TIP"


@pytest.mark.asyncio
async def test_status_code_mapping_tf():
    """Test TF (Transaction Failed) status mapping"""
    callback_data = AirtelMoneyCallbackFixtures.payment_failed()
    assert callback_data["transaction"]["status"] == "TF"


# =============================================================================
# Integration Tests - Full Flow
# =============================================================================

@pytest.mark.asyncio
async def test_complete_payment_flow(db_session, mock_httpx_client):
    """Test complete Push Payment flow from initiation to callback"""
    airtel_service = AirtelMoneyService(db_session=db_session, environment="staging")

    # 1. Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # 2. Initiate Push Payment
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        transaction_id = f"flow_test_{uuid4().hex[:10]}"
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": transaction_id,
                    "status": "TIP"
                }
            },
            "status": {"code": "200", "success": True}
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.push_payment(
                phone_number="254700123456",
                amount=1000.0,
                currency="KES",
                transaction_id=transaction_id,
                country_code="KE"
            )

    assert result["success"] is True
    assert result["status"] == "TIP"

    # 3. Process callback (simulate Airtel response)
    callback_data = AirtelMoneyCallbackFixtures.payment_success()
    callback_data["transaction"]["id"] = transaction_id

    await airtel_webhooks.process_payment_callback(callback_data, db_session)

    # 4. Verify callback stored in database
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(MMOCallback).where(
            MMOCallback.provider == "airtel_money",
            MMOCallback.provider_transaction_id == transaction_id
        )
    )
    callback = db_result.scalar_one_or_none()

    assert callback is not None
    assert callback.status == "successful"
    assert callback.callback_type == "payment"


@pytest.mark.asyncio
async def test_complete_disbursement_flow(db_session, mock_httpx_client):
    """Test complete Disbursement flow"""
    airtel_service = AirtelMoneyService(db_session=db_session, environment="staging")

    # 1. Mock access token
    with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
        # 2. Initiate Disbursement
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        transaction_id = f"disb_flow_{uuid4().hex[:10]}"
        mock_response.json.return_value = {
            "data": {
                "transaction": {
                    "id": transaction_id,
                    "status": "TS"
                }
            },
            "status": {"code": "200", "success": True}
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            result = await airtel_service.disbursement(
                phone_number="254700123456",
                amount=5000.0,
                currency="KES",
                transaction_id=transaction_id,
                country_code="KE"
            )

    assert result["success"] is True

    # 3. Process callback
    callback_data = AirtelMoneyCallbackFixtures.disbursement_success()
    callback_data["transaction"]["id"] = transaction_id

    await airtel_webhooks.process_disbursement_callback(callback_data, db_session)

    # 4. Verify callback
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(MMOCallback).where(
            MMOCallback.provider == "airtel_money",
            MMOCallback.provider_transaction_id == transaction_id
        )
    )
    callback = db_result.scalar_one_or_none()

    assert callback is not None
    assert callback.callback_type == "disbursement"


@pytest.mark.asyncio
async def test_webhook_health_endpoint():
    """Test Airtel webhook health check endpoint"""
    response = await airtel_webhooks.airtel_webhook_health()

    assert response["status"] == "healthy"
    assert response["provider"] == "airtel_money"


@pytest.mark.asyncio
async def test_multiple_country_support(airtel_service, mock_httpx_client):
    """Test Airtel Money works across multiple countries"""
    countries = [
        ("KE", "254700123456", "KES"),
        ("TZ", "255700123456", "TZS"),
        ("UG", "256774123456", "UGX"),
        ("RW", "250788123456", "RWF"),
    ]

    for country_code, phone, currency in countries:
        # Mock access token
        with patch.object(airtel_service, '_get_access_token', return_value="test_token"):
            # Mock successful response
            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "transaction": {
                        "id": f"{country_code}_test",
                        "status": "TS"
                    }
                },
                "status": {"code": "200", "success": True}
            }
            mock_httpx_client.post = AsyncMock(return_value=mock_response)

            with patch("httpx.AsyncClient", return_value=mock_httpx_client):
                result = await airtel_service.push_payment(
                    phone_number=phone,
                    amount=1000.0,
                    currency=currency,
                    transaction_id=f"{country_code}_test",
                    country_code=country_code
                )

        assert result["success"] is True, f"Failed for country {country_code}"


if __name__ == "__main__":
    print("Run with: pytest tests/integration/test_airtel_money_integration.py -v")
