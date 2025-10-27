# M-Pesa Integration Test Guide

Comprehensive guide for testing M-Pesa payment integration in CAPP.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Prerequisites](#prerequisites)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Test Fixtures](#test-fixtures)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)

## Overview

The M-Pesa test suite validates the complete M-Pesa integration including:

- **Database Operations**: Transaction and callback persistence
- **Repository Layer**: CRUD operations and queries
- **Webhook Endpoints**: Callback processing and validation
- **Error Handling**: Edge cases and failure scenarios
- **Complete Flows**: End-to-end transaction lifecycles

## Test Structure

```
tests/
├── fixtures/
│   ├── __init__.py
│   └── mpesa_callbacks.py          # Sample M-Pesa callback data
├── integration/
│   └── test_mpesa_integration.py   # Integration tests with database
└── unit/
    └── test_mpesa_repository.py    # Unit tests with mocked dependencies
```

### Test Types

1. **Unit Tests** (`tests/unit/test_mpesa_repository.py`)
   - Test repository methods in isolation
   - Mock database connections
   - Fast execution
   - 40+ test cases

2. **Integration Tests** (`tests/integration/test_mpesa_integration.py`)
   - Test with real database connections
   - Validate complete workflows
   - Test webhook endpoints
   - 30+ test cases

3. **Test Fixtures** (`tests/fixtures/mpesa_callbacks.py`)
   - Sample M-Pesa callback data
   - Reusable across test suites
   - Covers all callback types

## Prerequisites

### Database Setup

1. **PostgreSQL Installation**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib

   # macOS
   brew install postgresql
   ```

2. **Create Test Database**
   ```bash
   # Create database
   createdb capp_test

   # Or via psql
   psql -U postgres
   CREATE DATABASE capp_test;
   ```

3. **Run Migrations**
   ```bash
   # Set test database URL
   export DATABASE_URL="postgresql://postgres:password@localhost:5432/capp_test"

   # Run migrations
   cd applications/capp
   alembic upgrade head
   ```

### Python Dependencies

```bash
# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
```

## Running Tests

### Run All M-Pesa Tests

```bash
# From project root
pytest tests/unit/test_mpesa_repository.py tests/integration/test_mpesa_integration.py -v
```

### Run Unit Tests Only

```bash
pytest tests/unit/test_mpesa_repository.py -v
```

### Run Integration Tests Only

```bash
# Requires PostgreSQL running
pytest tests/integration/test_mpesa_integration.py -v
```

### Run Specific Test

```bash
pytest tests/unit/test_mpesa_repository.py::test_create_transaction_basic -v
```

### Run with Coverage

```bash
pytest tests/unit/test_mpesa_repository.py \
       tests/integration/test_mpesa_integration.py \
       --cov=applications.capp.capp.repositories.mpesa \
       --cov=applications.capp.capp.api.v1.endpoints.webhooks \
       --cov-report=html
```

### Run with Markers

```bash
# Run only async tests
pytest -m asyncio -v

# Skip slow tests
pytest -m "not slow" -v
```

## Test Coverage

### Repository Tests (Unit)

**Transaction Operations**
- ✅ Create transaction (basic)
- ✅ Create transaction (with all fields)
- ✅ Get by ID (found/not found)
- ✅ Get by checkout request ID
- ✅ Get by merchant request ID
- ✅ Get by conversation ID
- ✅ Get by receipt number
- ✅ Get by payment ID
- ✅ Update transaction status
- ✅ Update with receipt number
- ✅ Update to processing status
- ✅ Update transaction not found
- ✅ Increment retry count

**Callback Operations**
- ✅ Create callback
- ✅ Get callback by ID
- ✅ Get callbacks by transaction
- ✅ Mark callback processed (success)
- ✅ Mark callback processed (with error)
- ✅ Verify callback signature

**Query Operations**
- ✅ Get pending transactions
- ✅ Get unprocessed callbacks
- ✅ Get transaction statistics
- ✅ Get transactions by phone
- ✅ Get failed transactions
- ✅ Statistics with no data

**Edge Cases**
- ✅ Zero amount transaction
- ✅ Multiple field updates
- ✅ Empty statistics

### Integration Tests (With Database)

**Database Operations**
- ✅ Create M-Pesa transaction
- ✅ Retrieve by checkout request ID
- ✅ Update transaction
- ✅ Create callback record
- ✅ Mark callback processed
- ✅ Get pending transactions
- ✅ Get transaction statistics
- ✅ Get by receipt number
- ✅ Increment retry count
- ✅ Get unprocessed callbacks

**Webhook Endpoints**
- ✅ STK Push success callback
- ✅ STK Push failed callback
- ✅ STK Push timeout callback
- ✅ B2C result callback
- ✅ C2B confirmation
- ✅ C2B validation
- ✅ Account balance result
- ✅ Transaction status result

**Complete Flows**
- ✅ Complete STK Push flow (initiation → callback → completion)
- ✅ Complete B2C flow (initiation → result)
- ✅ Failed transaction handling
- ✅ Timeout handling
- ✅ Callback processing with database persistence

## Test Fixtures

### Available Fixtures

The `MpesaCallbackFixtures` class provides sample data for all M-Pesa callback types:

```python
from tests.fixtures import MpesaCallbackFixtures

# STK Push callbacks
MpesaCallbackFixtures.stk_push_success()
MpesaCallbackFixtures.stk_push_user_cancelled()
MpesaCallbackFixtures.stk_push_insufficient_funds()
MpesaCallbackFixtures.stk_push_invalid_phone()
MpesaCallbackFixtures.stk_push_timeout()

# B2C callbacks
MpesaCallbackFixtures.b2c_success()
MpesaCallbackFixtures.b2c_failed_insufficient_funds()
MpesaCallbackFixtures.b2c_invalid_receiver()

# C2B callbacks
MpesaCallbackFixtures.c2b_confirmation()
MpesaCallbackFixtures.c2b_validation()

# Query callbacks
MpesaCallbackFixtures.account_balance_success()
MpesaCallbackFixtures.transaction_status_success()
MpesaCallbackFixtures.transaction_status_not_found()

# Reversal callbacks
MpesaCallbackFixtures.reversal_success()
MpesaCallbackFixtures.reversal_failed()
```

### Result Codes

```python
from tests.fixtures import MPESA_RESULT_CODES, get_result_description

# Get description for result code
description = get_result_description(0)  # "Success"
description = get_result_description(1032)  # "Cancelled by User"
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from applications.capp.capp.repositories.mpesa import MpesaRepository

@pytest.mark.asyncio
async def test_your_feature(mock_session):
    """Test description"""
    # Arrange
    repo = MpesaRepository(mock_session)

    # Act
    result = await repo.your_method()

    # Assert
    assert result is not None
    mock_session.commit.assert_called_once()
```

### Integration Test Template

```python
import pytest
from applications.capp.capp.repositories.mpesa import MpesaRepository

@pytest.mark.asyncio
async def test_your_feature_integration(db_session):
    """Test description"""
    # Arrange
    repo = MpesaRepository(db_session)

    # Act
    result = await repo.your_method()

    # Assert
    assert result is not None
```

### Webhook Test Template

```python
import pytest
from unittest.mock import Mock, AsyncMock
from tests.fixtures import MpesaCallbackFixtures

@pytest.mark.asyncio
async def test_your_webhook(db_session):
    """Test description"""
    # Arrange
    callback_data = MpesaCallbackFixtures.stk_push_success()
    request = Mock()
    request.body = AsyncMock(return_value=json.dumps(callback_data).encode())

    # Act
    response = await webhooks.your_endpoint(request, db_session)

    # Assert
    assert response.status_code == 200
```

## Testing Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
@pytest.fixture
async def db_session():
    """Each test gets fresh session"""
    async with AsyncSessionLocal() as session:
        yield session
```

### 2. Use Fixtures

Reuse common setup code:

```python
@pytest.fixture
def sample_transaction():
    """Create reusable transaction"""
    return MpesaTransaction(
        id=uuid4(),
        transaction_type="stk_push",
        phone_number="254708374149",
        amount=Decimal("1000.00"),
        status="pending"
    )
```

### 3. Mock External Dependencies

Mock M-Pesa API calls, not database operations:

```python
@patch('applications.capp.capp.services.mpesa_integration.requests.post')
async def test_initiate_stk_push(mock_post):
    """Test STK Push initiation"""
    mock_post.return_value.json.return_value = {"ResponseCode": "0"}
    # Test implementation
```

### 4. Test Edge Cases

Always test error conditions:

```python
@pytest.mark.asyncio
async def test_transaction_not_found(mpesa_repo):
    """Test handling of non-existent transaction"""
    transaction = await mpesa_repo.get_by_id(uuid4())
    assert transaction is None
```

### 5. Use Descriptive Names

Test names should explain what they test:

```python
# Good
async def test_stk_push_callback_updates_transaction_status()

# Bad
async def test_callback()
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql

# Verify connection
psql -U postgres -d capp_test
```

#### 2. Migration Not Applied

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "mpesa_transactions" does not exist
```

**Solution:**
```bash
# Run migrations
cd applications/capp
export DATABASE_URL="postgresql://postgres:password@localhost:5432/capp_test"
alembic upgrade head
```

#### 3. Import Errors

```
ModuleNotFoundError: No module named 'applications'
```

**Solution:**
```bash
# Run from project root
cd /home/user/CAPP
pytest tests/unit/test_mpesa_repository.py -v

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/home/user/CAPP"
```

#### 4. Async Test Not Running

```
RuntimeWarning: coroutine 'test_create_transaction' was never awaited
```

**Solution:**
```python
# Add pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_create_transaction():
    # Test implementation
```

#### 5. Database Not Cleaned Between Tests

**Solution:**
```python
@pytest.fixture(scope="module")
async def setup_database():
    """Set up test database"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: M-Pesa Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: capp_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r applications/capp/requirements.txt
          pip install pytest pytest-asyncio httpx

      - name: Run migrations
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/capp_test
        run: |
          cd applications/capp
          alembic upgrade head

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/capp_test
        run: |
          pytest tests/unit/test_mpesa_repository.py \
                 tests/integration/test_mpesa_integration.py \
                 -v --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Maintenance

### Adding New Callback Types

1. Add fixture to `tests/fixtures/mpesa_callbacks.py`:
   ```python
   @staticmethod
   def new_callback_type() -> Dict[str, Any]:
       """Description"""
       return { ... }
   ```

2. Add unit test to `tests/unit/test_mpesa_repository.py`:
   ```python
   @pytest.mark.asyncio
   async def test_new_callback_processing(mpesa_repo, mock_session):
       # Test implementation
   ```

3. Add integration test to `tests/integration/test_mpesa_integration.py`:
   ```python
   @pytest.mark.asyncio
   async def test_new_callback_integration(db_session):
       # Test implementation with database
   ```

### Updating for Schema Changes

When database schema changes:

1. Update fixtures to match new schema
2. Update test assertions
3. Run migration: `alembic upgrade head`
4. Verify all tests pass

## Performance Testing

### Benchmark Tests

```python
import time

@pytest.mark.asyncio
async def test_transaction_creation_performance(db_session):
    """Test transaction creation performance"""
    repo = MpesaRepository(db_session)

    start = time.time()
    for i in range(100):
        await repo.create_transaction(
            transaction_type="stk_push",
            phone_number=f"25470837414{i}",
            amount=Decimal("1000.00")
        )
    duration = time.time() - start

    # Should create 100 transactions in under 5 seconds
    assert duration < 5.0
```

## Support

For questions or issues:
- Check this guide first
- Review test examples in the codebase
- Check [Phase 3.2 Implementation Plan](../docs/PHASE_3.2_MMO_INTEGRATION_PLAN.md)
- Review [Database Migrations Guide](../docs/DATABASE_MIGRATIONS.md)

## Summary

✅ **70+ Test Cases** covering M-Pesa integration
✅ **Unit Tests** for repository logic
✅ **Integration Tests** with database
✅ **Webhook Tests** for all callback types
✅ **Complete Flow Tests** end-to-end
✅ **Comprehensive Fixtures** for reusable test data
✅ **Documentation** for writing and maintaining tests

**Next Steps:**
1. Run test suite: `pytest tests/unit/test_mpesa_repository.py tests/integration/test_mpesa_integration.py -v`
2. Check coverage: Add `--cov` flag
3. Add CI/CD: Integrate with GitHub Actions
4. Monitor: Track test failures and fix promptly
