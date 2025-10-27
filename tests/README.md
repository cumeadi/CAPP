# Canza Platform Testing Suite

**Comprehensive Testing Suite for SDK Performance Validation**

This testing suite validates that the Canza Agent Framework SDK achieves the same performance as the original CAPP system, ensuring **91% cost reduction** and **1.5-second processing time** are maintained.

## 🎯 **Testing Overview**

### **What We Test**

The testing suite validates:

- ✅ **91% Cost Reduction** - Payment optimization performance
- ✅ **1.5s Processing Time** - Transaction processing speed
- ✅ **95%+ Success Rate** - System reliability
- ✅ **Multi-Agent Coordination** - Framework orchestration
- ✅ **Integration Components** - Mobile money, blockchain, banking
- ✅ **Performance Consistency** - Stable performance over time
- ✅ **Scalability** - Load testing and concurrent processing
- ✅ **Memory & CPU Usage** - Resource efficiency

### **Testing Structure**

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_payment_optimizer_agent.py
│   ├── test_compliance_agent.py
│   ├── test_risk_agent.py
│   └── test_orchestration.py
├── integration/             # Integration tests for components working together
│   ├── test_sdk_framework.py
│   ├── test_capp_reference.py
│   └── test_integrations.py
├── performance/             # Performance benchmarks and load testing
│   ├── test_sdk_performance.py
│   ├── test_load_testing.py
│   └── test_scalability.py
├── e2e/                     # End-to-end tests for complete workflows
│   ├── test_payment_flow.py
│   ├── test_cross_border.py
│   └── test_error_handling.py
└── sdk/                     # SDK validation tests
    ├── test_examples.py
    ├── test_installation.py
    └── test_developer_experience.py
```

## 🚀 **Quick Start**

### **Installation**

```bash
# Install testing dependencies
pip install -r requirements-test.txt

# Install the SDK for testing
pip install -e .
```

### **Run All Tests**

```bash
# Run complete test suite
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ --cov=canza_agents --cov-report=html --cov-report=term
```

### **Run Specific Test Categories**

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Performance tests only
pytest tests/performance/ -v

# End-to-end tests only
pytest tests/e2e/ -v

# SDK validation tests only
pytest tests/sdk/ -v
```

## 📊 **Test Categories**

### **Unit Tests (`tests/unit/`)**

Unit tests validate individual components in isolation:

#### **Payment Optimizer Agent Tests**
- **Agent Initialization** - Configuration and setup validation
- **Transaction Processing** - Basic payment optimization
- **Cost Reduction Achievement** - 91% cost reduction validation
- **Processing Time Performance** - 1.5s processing time validation
- **Route Discovery** - Payment route finding logic
- **Route Scoring** - Multi-criteria route evaluation
- **Optimal Route Selection** - Best route selection logic
- **Cross-border Optimization** - International payment handling
- **Optimization Strategies** - Different optimization approaches
- **Learning Functionality** - Agent adaptation and learning
- **Error Handling** - Graceful error management
- **Performance Consistency** - Stable performance over time

#### **Compliance Agent Tests**
- **KYC Verification** - Know-your-customer validation
- **AML Screening** - Anti-money laundering checks
- **Sanctions Screening** - Sanctions list validation
- **Regulatory Compliance** - Jurisdiction-specific rules
- **Risk Assessment** - Transaction risk evaluation

#### **Risk Assessment Agent Tests**
- **Risk Scoring** - Transaction risk calculation
- **Fraud Detection** - Fraud pattern recognition
- **Risk Thresholds** - Risk level determination
- **Recommendations** - Risk-based recommendations

### **Integration Tests (`tests/integration/`)**

Integration tests validate components working together:

#### **SDK Framework Integration**
- **Framework Initialization** - Complete framework setup
- **Multi-Agent Coordination** - Agent collaboration
- **Consensus Mechanism** - Agent agreement validation
- **Learning Integration** - Cross-agent learning
- **Analytics Integration** - Performance metrics collection
- **Workflow Integration** - Custom workflow execution

#### **CAPP Reference Implementation**
- **Performance Validation** - CAPP performance replication
- **API Compatibility** - CAPP API compatibility
- **Configuration Management** - CAPP configuration handling

#### **External Integrations**
- **Mobile Money Integration** - M-Pesa, MTN MoMo, Airtel Money
- **Blockchain Integration** - Aptos settlement and liquidity
- **Banking Integration** - SWIFT, SEPA, ACH integration

### **Performance Tests (`tests/performance/`)**

Performance tests benchmark system performance:

#### **91% Cost Reduction Benchmark**
- **Target Achievement** - Validates 91% cost reduction
- **Consistency Testing** - Performance stability over time
- **Edge Case Testing** - Large amounts, cross-border, urgent payments
- **Provider Optimization** - Multi-provider cost optimization

#### **1.5s Processing Time Benchmark**
- **Speed Validation** - Sub-second processing achievement
- **Latency Testing** - Processing time consistency
- **Concurrent Processing** - Multi-transaction handling
- **Resource Optimization** - CPU and memory efficiency

#### **Load Testing & Scalability**
- **Concurrent Transactions** - 10, 50, 100, 200, 500 transactions
- **Throughput Testing** - Transactions per second
- **Resource Usage** - Memory and CPU monitoring
- **Performance Degradation** - Performance under load

#### **Performance Consistency**
- **Batch Processing** - Multiple transaction batches
- **Statistical Analysis** - Mean, standard deviation, percentiles
- **Coefficient of Variation** - Performance stability metrics

### **End-to-End Tests (`tests/e2e/`)**

End-to-end tests validate complete workflows:

#### **Complete Payment Flow**
- **Transaction Creation** - Payment request generation
- **Optimization Process** - Multi-agent optimization
- **Route Selection** - Optimal route determination
- **Payment Execution** - Actual payment processing
- **Settlement** - Payment settlement and confirmation

#### **Cross-border Payment Scenarios**
- **International Transfers** - Cross-border payment flows
- **Currency Conversion** - Multi-currency handling
- **Regulatory Compliance** - Cross-border regulations
- **Settlement Time** - International settlement timing

#### **Error Handling & Recovery**
- **Network Failures** - Connection loss handling
- **Provider Failures** - Payment provider failures
- **Invalid Transactions** - Malformed request handling
- **Recovery Mechanisms** - Automatic retry and fallback

### **SDK Validation Tests (`tests/sdk/`)**

SDK validation tests ensure developer experience:

#### **Example Validation**
- **Quick Start Example** - 5-minute tutorial validation
- **Custom Agent Example** - Custom agent development
- **Integration Example** - External system integration
- **Performance Example** - Performance optimization examples

#### **Installation & Setup**
- **Package Installation** - SDK installation process
- **Dependency Management** - Required dependencies
- **Configuration Setup** - Environment configuration
- **Initialization Process** - Framework initialization

#### **Developer Experience**
- **API Usability** - API ease of use
- **Documentation Accuracy** - Documentation validation
- **Error Messages** - Clear error reporting
- **Debugging Support** - Debug mode and logging

## 📈 **Performance Benchmarks**

### **Target Performance Metrics**

| Metric | Target | Acceptable Range | Test Validation |
|--------|--------|------------------|-----------------|
| **Cost Reduction** | 91% | 85-95% | `test_91_percent_cost_reduction_benchmark` |
| **Processing Time** | 1.5s | 1.0-2.0s | `test_1_5_second_processing_time_benchmark` |
| **Success Rate** | 95% | 90-98% | `test_success_rate_validation` |
| **Concurrent Processing** | 100 txn/s | 50-200 txn/s | `test_load_testing_scalability` |
| **Memory Usage** | <500MB | <1GB | `test_memory_usage_benchmark` |
| **CPU Usage** | <80% | <95% | `test_cpu_usage_benchmark` |

### **Performance Validation Process**

1. **Baseline Establishment** - Original CAPP performance baseline
2. **SDK Performance Testing** - SDK performance measurement
3. **Comparison Analysis** - SDK vs CAPP performance comparison
4. **Acceptance Criteria** - Performance threshold validation
5. **Regression Testing** - Performance consistency over time

## 🔧 **Test Configuration**

### **Environment Setup**

```bash
# Test environment variables
export CANZA_TEST_MODE=true
export CANZA_TEST_REGION=africa
export CANZA_TEST_COMPLIANCE_LEVEL=standard
export REDIS_TEST_URL=redis://localhost:6379/1
export DATABASE_TEST_URL=postgresql://test:test@localhost:5432/canza_test
```

### **Test Configuration File**

```python
# tests/conftest.py
import pytest
import asyncio
from canza_agents import FinancialFramework, Region, ComplianceLevel

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_framework():
    """Create test framework instance"""
    framework = FinancialFramework(
        region=Region.AFRICA,
        compliance_level=ComplianceLevel.STANDARD
    )
    await framework.initialize()
    yield framework
    await framework.shutdown()
```

### **Mock Services**

```python
# tests/mocks/
├── mock_mobile_money.py      # Mobile money provider mocks
├── mock_blockchain.py        # Blockchain network mocks
├── mock_banking.py           # Banking API mocks
└── mock_external_apis.py     # External service mocks
```

## 📊 **Test Results & Reporting**

### **Test Execution**

```bash
# Run tests with detailed output
pytest tests/ -v --tb=short --durations=10

# Generate HTML coverage report
pytest tests/ --cov=canza_agents --cov-report=html

# Generate performance report
pytest tests/performance/ -v --benchmark-only
```

### **Coverage Requirements**

- **Code Coverage**: >95% overall coverage
- **Critical Path Coverage**: 100% for payment optimization
- **Integration Coverage**: >90% for component interactions
- **Performance Coverage**: 100% for performance-critical paths

### **Performance Reports**

```bash
# Generate performance benchmark report
python -m pytest tests/performance/test_sdk_performance.py::TestSDKPerformance::test_91_percent_cost_reduction_benchmark -v -s

# Generate load testing report
python -m pytest tests/performance/test_sdk_performance.py::TestSDKPerformance::test_load_testing_scalability -v -s
```

## 🚨 **Continuous Integration**

### **CI/CD Pipeline**

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements-test.txt
        pip install -e .
    
    - name: Run unit tests
      run: pytest tests/unit/ --cov=canza_agents --cov-report=xml
    
    - name: Run integration tests
      run: pytest tests/integration/ --cov=canza_agents --cov-report=xml
    
    - name: Run performance tests
      run: pytest tests/performance/ -v
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

### **Performance Monitoring**

```python
# tests/performance/monitor.py
import time
import statistics
from typing import List, Dict

class PerformanceMonitor:
    """Monitor and report performance metrics"""
    
    def __init__(self):
        self.metrics = []
    
    def record_metric(self, test_name: str, metric: str, value: float):
        """Record a performance metric"""
        self.metrics.append({
            "test": test_name,
            "metric": metric,
            "value": value,
            "timestamp": time.time()
        })
    
    def generate_report(self) -> Dict:
        """Generate performance report"""
        return {
            "total_tests": len(set(m["test"] for m in self.metrics)),
            "metrics": self.metrics,
            "summary": self._calculate_summary()
        }
    
    def _calculate_summary(self) -> Dict:
        """Calculate performance summary"""
        cost_savings = [m["value"] for m in self.metrics if m["metric"] == "cost_savings"]
        processing_times = [m["value"] for m in self.metrics if m["metric"] == "processing_time"]
        
        return {
            "avg_cost_savings": statistics.mean(cost_savings) if cost_savings else 0,
            "avg_processing_time": statistics.mean(processing_times) if processing_times else 0,
            "min_cost_savings": min(cost_savings) if cost_savings else 0,
            "max_processing_time": max(processing_times) if processing_times else 0
        }
```

## 🔍 **Troubleshooting**

### **Common Test Issues**

#### **Import Errors**
```bash
# Ensure SDK is installed
pip install -e .

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### **Redis Connection Issues**
```bash
# Start Redis for testing
redis-server --port 6379

# Test Redis connection
redis-cli ping
```

#### **Performance Test Failures**
```bash
# Run performance tests with more time
pytest tests/performance/ --timeout=300

# Run with debug output
pytest tests/performance/ -v -s --log-cli-level=DEBUG
```

#### **Memory Issues**
```bash
# Increase memory limit for tests
pytest tests/ --max-memory=2GB

# Run with garbage collection
pytest tests/ --gc-collect
```

### **Debug Mode**

```python
# Enable debug mode for tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Run tests with debug output
pytest tests/ -v -s --log-cli-level=DEBUG
```

## 📚 **Test Documentation**

### **Writing New Tests**

```python
# Example test structure
import pytest
from canza_agents import FinancialFramework

class TestNewFeature:
    """Test suite for new feature"""
    
    @pytest.fixture
    async def framework(self):
        """Create test framework"""
        framework = FinancialFramework()
        await framework.initialize()
        yield framework
        await framework.shutdown()
    
    @pytest.mark.asyncio
    async def test_new_feature(self, framework):
        """Test new feature functionality"""
        # Test implementation
        result = await framework.new_feature()
        
        # Assertions
        assert result.success is True
        assert result.performance_metric >= expected_value
```

### **Performance Test Guidelines**

1. **Baseline Establishment** - Establish performance baselines
2. **Statistical Significance** - Use sufficient sample sizes
3. **Environment Consistency** - Ensure consistent test environment
4. **Resource Monitoring** - Monitor CPU, memory, and network usage
5. **Regression Detection** - Detect performance regressions

### **Integration Test Guidelines**

1. **Component Isolation** - Test components in isolation first
2. **Mock External Services** - Mock external dependencies
3. **Error Scenarios** - Test error conditions and edge cases
4. **Performance Validation** - Validate performance in integration
5. **End-to-End Validation** - Test complete workflows

## 💰 **M-Pesa Integration Tests**

### **Overview**

Phase 3.2 introduces comprehensive M-Pesa payment integration tests:

```
tests/
├── fixtures/
│   ├── __init__.py
│   └── mpesa_callbacks.py          # Sample M-Pesa callback data
├── integration/
│   ├── test_agent_database_integration.py
│   └── test_mpesa_integration.py   # M-Pesa integration tests
└── unit/
    ├── test_payment_optimizer_agent.py
    └── test_mpesa_repository.py    # M-Pesa repository unit tests
```

### **M-Pesa Test Coverage**

- ✅ **Repository Operations** - CRUD operations for transactions and callbacks
- ✅ **Webhook Endpoints** - STK Push, B2C, C2B, timeout callbacks
- ✅ **Database Persistence** - Transaction and callback storage
- ✅ **Complete Flows** - End-to-end payment lifecycles
- ✅ **Error Scenarios** - Edge cases and failure handling
- ✅ **70+ Test Cases** - Comprehensive coverage

### **Running M-Pesa Tests**

```bash
# Run all M-Pesa tests
pytest tests/unit/test_mpesa_repository.py tests/integration/test_mpesa_integration.py -v

# Run unit tests only
pytest tests/unit/test_mpesa_repository.py -v

# Run integration tests only (requires PostgreSQL)
pytest tests/integration/test_mpesa_integration.py -v

# Run with coverage
pytest tests/unit/test_mpesa_repository.py tests/integration/test_mpesa_integration.py \
       --cov=applications.capp.capp.repositories.mpesa \
       --cov=applications.capp.capp.api.v1.endpoints.webhooks \
       --cov-report=html
```

### **M-Pesa Test Documentation**

For comprehensive M-Pesa testing guide, see: [MPESA_TEST_GUIDE.md](MPESA_TEST_GUIDE.md)

Topics covered:
- Test structure and organization
- Database setup requirements
- Running tests and interpreting results
- Writing new M-Pesa tests
- Test fixtures and mock data
- Troubleshooting common issues
- CI/CD integration

---

**🎉 The comprehensive testing suite validates that the Canza Agent Framework SDK maintains all the performance advantages of the original CAPP system!**

**Run the tests to verify 91% cost reduction and 1.5s processing time achievement.**

**Built with ❤️ by the Canza Team**

*Comprehensive testing for enterprise-grade performance validation.* 