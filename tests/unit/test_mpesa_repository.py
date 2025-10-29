"""
Unit Tests for M-Pesa Repository

Tests M-Pesa repository methods in isolation with mocked database operations.

Run with: pytest tests/unit/test_mpesa_repository.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from applications.capp.capp.repositories.mpesa import MpesaRepository
from applications.capp.capp.core.database import MpesaTransaction, MpesaCallback


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Create mock database session"""
    session = Mock(spec=AsyncSession)
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mpesa_repo(mock_session):
    """Create M-Pesa repository with mock session"""
    return MpesaRepository(mock_session)


@pytest.fixture
def sample_transaction():
    """Create sample M-Pesa transaction"""
    return MpesaTransaction(
        id=uuid4(),
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        checkout_request_id="ws_CO_test123",
        merchant_request_id="MR_test123",
        status="pending",
        retry_count=0,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_callback():
    """Create sample M-Pesa callback"""
    return MpesaCallback(
        id=uuid4(),
        callback_type="stk_push",
        callback_data='{"test": "data"}',
        processed=False,
        processing_attempts=0,
        received_at=datetime.utcnow()
    )


# =============================================================================
# Transaction Creation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_transaction_basic(mpesa_repo, mock_session):
    """Test basic transaction creation"""
    transaction = await mpesa_repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00")
    )

    # Verify session methods called
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()

    # Verify transaction created
    assert transaction is not None
    assert transaction.transaction_type == "stk_push"
    assert transaction.phone_number == "254708374149"
    assert transaction.amount == Decimal("1000.00")
    assert transaction.status == "pending"


@pytest.mark.asyncio
async def test_create_transaction_with_all_fields(mpesa_repo, mock_session):
    """Test transaction creation with all optional fields"""
    payment_id = uuid4()

    transaction = await mpesa_repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        payment_id=payment_id,
        checkout_request_id="ws_CO_test123",
        merchant_request_id="MR_test123",
        conversation_id="AG_test123",
        account_reference="TEST001",
        transaction_desc="Test payment",
        request_payload={"key": "value"}
    )

    # Verify all fields set correctly
    assert transaction.payment_id == payment_id
    assert transaction.checkout_request_id == "ws_CO_test123"
    assert transaction.merchant_request_id == "MR_test123"
    assert transaction.conversation_id == "AG_test123"
    assert transaction.account_reference == "TEST001"
    assert transaction.transaction_desc == "Test payment"
    assert '"key": "value"' in transaction.request_payload


# =============================================================================
# Transaction Retrieval Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_by_id_found(mpesa_repo, mock_session, sample_transaction):
    """Test retrieving transaction by ID - found"""
    # Mock result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_transaction
    mock_session.execute.return_value = mock_result

    # Get transaction
    transaction = await mpesa_repo.get_by_id(sample_transaction.id)

    assert transaction is not None
    assert transaction.id == sample_transaction.id
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_not_found(mpesa_repo, mock_session):
    """Test retrieving transaction by ID - not found"""
    # Mock result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Get transaction
    transaction = await mpesa_repo.get_by_id(uuid4())

    assert transaction is None


@pytest.mark.asyncio
async def test_get_by_checkout_request_id(mpesa_repo, mock_session, sample_transaction):
    """Test retrieving transaction by checkout request ID"""
    # Mock result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_transaction
    mock_session.execute.return_value = mock_result

    # Get transaction
    transaction = await mpesa_repo.get_by_checkout_request_id("ws_CO_test123")

    assert transaction is not None
    assert transaction.checkout_request_id == sample_transaction.checkout_request_id


@pytest.mark.asyncio
async def test_get_by_receipt_number(mpesa_repo, mock_session, sample_transaction):
    """Test retrieving transaction by M-Pesa receipt number"""
    sample_transaction.mpesa_receipt_number = "NLJ7RT61SV"

    # Mock result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = sample_transaction
    mock_session.execute.return_value = mock_result

    # Get transaction
    transaction = await mpesa_repo.get_by_receipt_number("NLJ7RT61SV")

    assert transaction is not None
    assert transaction.mpesa_receipt_number == "NLJ7RT61SV"


@pytest.mark.asyncio
async def test_get_by_payment_id(mpesa_repo, mock_session):
    """Test retrieving all transactions for a payment"""
    payment_id = uuid4()
    transactions = [
        MpesaTransaction(
            id=uuid4(),
            payment_id=payment_id,
            transaction_type="stk_push",
            phone_number="254708374149",
            amount=Decimal("1000.00"),
            status="completed"
        ),
        MpesaTransaction(
            id=uuid4(),
            payment_id=payment_id,
            transaction_type="stk_push",
            phone_number="254708374149",
            amount=Decimal("1000.00"),
            status="failed"
        )
    ]

    # Mock result
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all.return_value = transactions
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    # Get transactions
    result = await mpesa_repo.get_by_payment_id(payment_id)

    assert len(result) == 2
    assert all(t.payment_id == payment_id for t in result)


# =============================================================================
# Transaction Update Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_transaction_status(mpesa_repo, mock_session, sample_transaction):
    """Test updating transaction status"""
    # Mock get_by_id
    with patch.object(mpesa_repo, 'get_by_id', return_value=sample_transaction):
        updated = await mpesa_repo.update_transaction(
            transaction_id=sample_transaction.id,
            status="completed",
            result_code=0,
            result_description="Success"
        )

    assert updated.status == "completed"
    assert updated.result_code == 0
    assert updated.result_description == "Success"
    assert updated.completed_at is not None
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_transaction_with_receipt(mpesa_repo, mock_session, sample_transaction):
    """Test updating transaction with receipt number"""
    # Mock get_by_id
    with patch.object(mpesa_repo, 'get_by_id', return_value=sample_transaction):
        updated = await mpesa_repo.update_transaction(
            transaction_id=sample_transaction.id,
            mpesa_receipt_number="NLJ7RT61SV",
            transaction_date=datetime.utcnow()
        )

    assert updated.mpesa_receipt_number == "NLJ7RT61SV"
    assert updated.transaction_date is not None


@pytest.mark.asyncio
async def test_update_transaction_not_found(mpesa_repo, mock_session):
    """Test updating non-existent transaction"""
    # Mock get_by_id returning None
    with patch.object(mpesa_repo, 'get_by_id', return_value=None):
        updated = await mpesa_repo.update_transaction(
            transaction_id=uuid4(),
            status="completed"
        )

    assert updated is None


@pytest.mark.asyncio
async def test_update_transaction_processing_status(mpesa_repo, mock_session, sample_transaction):
    """Test updating transaction to processing status"""
    # Mock get_by_id
    with patch.object(mpesa_repo, 'get_by_id', return_value=sample_transaction):
        updated = await mpesa_repo.update_transaction(
            transaction_id=sample_transaction.id,
            status="processing"
        )

    assert updated.status == "processing"
    assert updated.callback_received_at is not None


@pytest.mark.asyncio
async def test_increment_retry_count(mpesa_repo, mock_session, sample_transaction):
    """Test incrementing retry count"""
    initial_retry_count = sample_transaction.retry_count

    # Mock get_by_id
    with patch.object(mpesa_repo, 'get_by_id', return_value=sample_transaction):
        updated = await mpesa_repo.increment_retry_count(sample_transaction.id)

    assert updated.retry_count == initial_retry_count + 1
    assert updated.last_retry_at is not None


# =============================================================================
# Callback Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_callback(mpesa_repo, mock_session):
    """Test creating M-Pesa callback"""
    transaction_id = uuid4()

    callback = await mpesa_repo.create_callback(
        callback_type="stk_push",
        callback_data={"test": "data"},
        checkout_request_id="ws_CO_test123",
        mpesa_transaction_id=transaction_id
    )

    assert callback.callback_type == "stk_push"
    assert callback.mpesa_transaction_id == transaction_id
    assert callback.processed is False
    assert callback.signature_verified is False
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_mark_callback_processed_success(mpesa_repo, mock_session, sample_callback):
    """Test marking callback as successfully processed"""
    # Mock get_callback_by_id
    with patch.object(mpesa_repo, 'get_callback_by_id', return_value=sample_callback):
        updated = await mpesa_repo.mark_callback_processed(
            callback_id=sample_callback.id,
            success=True
        )

    assert updated.processed is True
    assert updated.processed_at is not None
    assert updated.processing_attempts == 1
    assert updated.processing_error is None


@pytest.mark.asyncio
async def test_mark_callback_processed_with_error(mpesa_repo, mock_session, sample_callback):
    """Test marking callback as processed with error"""
    # Mock get_callback_by_id
    with patch.object(mpesa_repo, 'get_callback_by_id', return_value=sample_callback):
        updated = await mpesa_repo.mark_callback_processed(
            callback_id=sample_callback.id,
            success=False,
            error="Processing failed"
        )

    assert updated.processing_error == "Processing failed"
    assert updated.processing_attempts == 1


@pytest.mark.asyncio
async def test_verify_callback_signature(mpesa_repo, mock_session, sample_callback):
    """Test verifying callback signature"""
    # Mock get_callback_by_id
    with patch.object(mpesa_repo, 'get_callback_by_id', return_value=sample_callback):
        updated = await mpesa_repo.verify_callback_signature(
            callback_id=sample_callback.id,
            verified=True
        )

    assert updated.signature_verified is True


@pytest.mark.asyncio
async def test_get_callbacks_by_transaction(mpesa_repo, mock_session):
    """Test retrieving all callbacks for a transaction"""
    transaction_id = uuid4()
    callbacks = [
        MpesaCallback(
            id=uuid4(),
            mpesa_transaction_id=transaction_id,
            callback_type="stk_push",
            callback_data='{"test": "data1"}',
            processed=True
        ),
        MpesaCallback(
            id=uuid4(),
            mpesa_transaction_id=transaction_id,
            callback_type="timeout",
            callback_data='{"test": "data2"}',
            processed=False
        )
    ]

    # Mock result
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all.return_value = callbacks
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    # Get callbacks
    result = await mpesa_repo.get_callbacks_by_transaction(transaction_id)

    assert len(result) == 2
    assert all(c.mpesa_transaction_id == transaction_id for c in result)


# =============================================================================
# Query and Analytics Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_pending_transactions(mpesa_repo, mock_session):
    """Test retrieving pending transactions"""
    old_time = datetime.utcnow() - timedelta(minutes=10)
    transactions = [
        MpesaTransaction(
            id=uuid4(),
            transaction_type="stk_push",
            phone_number="254708374149",
            amount=Decimal("1000.00"),
            status="pending",
            created_at=old_time
        )
    ]

    # Mock result
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all.return_value = transactions
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    # Get pending transactions
    result = await mpesa_repo.get_pending_transactions(minutes_old=5)

    assert len(result) >= 1
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_unprocessed_callbacks(mpesa_repo, mock_session):
    """Test retrieving unprocessed callbacks"""
    callbacks = [
        MpesaCallback(
            id=uuid4(),
            callback_type="stk_push",
            callback_data='{"test": "data"}',
            processed=False
        )
    ]

    # Mock result
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all.return_value = callbacks
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    # Get unprocessed callbacks
    result = await mpesa_repo.get_unprocessed_callbacks(limit=100)

    assert len(result) >= 1
    assert all(not c.processed for c in result)


@pytest.mark.asyncio
async def test_get_transaction_statistics(mpesa_repo, mock_session):
    """Test transaction statistics calculation"""
    # Mock multiple query results
    total_result = Mock()
    total_result.scalar.return_value = 100

    status_result = Mock()
    status_result.all.return_value = [
        ("completed", 70),
        ("failed", 20),
        ("pending", 10)
    ]

    amount_result = Mock()
    amount_result.scalar.return_value = Decimal("100000.00")

    completed_result = Mock()
    completed_result.scalar.return_value = 70

    # Mock execute to return different results for different queries
    mock_session.execute.side_effect = [
        total_result,
        status_result,
        amount_result,
        completed_result
    ]

    # Get statistics
    stats = await mpesa_repo.get_transaction_statistics(
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow()
    )

    assert stats["total_transactions"] == 100
    assert stats["completed_transactions"] == 70
    assert stats["success_rate"] == 70.0
    assert stats["total_amount"] == 100000.00
    assert "status_breakdown" in stats


@pytest.mark.asyncio
async def test_get_failed_transactions(mpesa_repo, mock_session):
    """Test retrieving failed transactions"""
    transactions = [
        MpesaTransaction(
            id=uuid4(),
            transaction_type="stk_push",
            phone_number="254708374149",
            amount=Decimal("1000.00"),
            status="failed",
            created_at=datetime.utcnow()
        ),
        MpesaTransaction(
            id=uuid4(),
            transaction_type="stk_push",
            phone_number="254708374150",
            amount=Decimal("500.00"),
            status="timeout",
            created_at=datetime.utcnow()
        )
    ]

    # Mock result
    mock_result = Mock()
    mock_scalars = Mock()
    mock_scalars.all.return_value = transactions
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    # Get failed transactions
    result = await mpesa_repo.get_failed_transactions(
        start_date=datetime.utcnow() - timedelta(days=7),
        limit=100
    )

    assert len(result) >= 2
    assert all(t.status in ["failed", "timeout", "cancelled"] for t in result)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

@pytest.mark.asyncio
async def test_create_transaction_with_zero_amount(mpesa_repo, mock_session):
    """Test creating transaction with zero amount (should be prevented by DB constraint)"""
    transaction = await mpesa_repo.create_transaction(
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("0")
    )

    # Repository allows it, but database constraint should prevent it
    assert transaction.amount == Decimal("0")


@pytest.mark.asyncio
async def test_update_transaction_multiple_fields(mpesa_repo, mock_session, sample_transaction):
    """Test updating multiple transaction fields at once"""
    # Mock get_by_id
    with patch.object(mpesa_repo, 'get_by_id', return_value=sample_transaction):
        updated = await mpesa_repo.update_transaction(
            transaction_id=sample_transaction.id,
            status="completed",
            result_code=0,
            result_description="Success",
            mpesa_receipt_number="NLJ7RT61SV",
            transaction_date=datetime.utcnow(),
            response_payload={"key": "value"}
        )

    assert updated.status == "completed"
    assert updated.result_code == 0
    assert updated.mpesa_receipt_number == "NLJ7RT61SV"
    assert '"key": "value"' in updated.response_payload


@pytest.mark.asyncio
async def test_get_transaction_statistics_empty(mpesa_repo, mock_session):
    """Test statistics with no transactions"""
    # Mock empty results
    total_result = Mock()
    total_result.scalar.return_value = 0

    status_result = Mock()
    status_result.all.return_value = []

    amount_result = Mock()
    amount_result.scalar.return_value = None

    completed_result = Mock()
    completed_result.scalar.return_value = 0

    mock_session.execute.side_effect = [
        total_result,
        status_result,
        amount_result,
        completed_result
    ]

    # Get statistics
    stats = await mpesa_repo.get_transaction_statistics()

    assert stats["total_transactions"] == 0
    assert stats["completed_transactions"] == 0
    assert stats["total_amount"] == 0.0
    assert stats["success_rate"] == 0


if __name__ == "__main__":
    print("Run with: pytest tests/unit/test_mpesa_repository.py -v")
