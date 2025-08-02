# Custom Agent Examples

Examples of building custom payment agents with the Canza Agent Framework.

## 🤖 Agent Types

This directory contains examples of different types of custom agents:

### 1. Route Optimization Agents

Advanced routing algorithms for payment optimization:

- **ML-Based Router**: Machine learning-powered route selection
- **Cost-Aware Router**: Route selection based on cost optimization
- **Speed-Optimized Router**: Route selection for fastest settlement
- **Compliance Router**: Route selection ensuring regulatory compliance

### 2. Cost Analysis Agents

Specialized agents for cost optimization:

- **Dynamic Pricing Agent**: Real-time pricing optimization
- **Bulk Discount Agent**: Volume-based discount calculation
- **Currency Arbitrage Agent**: Cross-currency optimization
- **Fee Optimization Agent**: Transaction fee minimization

### 3. Compliance Agents

Regulatory compliance automation:

- **KYC Agent**: Know Your Customer verification
- **AML Agent**: Anti-Money Laundering screening
- **Sanctions Agent**: Sanctions list checking
- **Regulatory Agent**: Country-specific compliance

### 4. Liquidity Management Agents

Dynamic liquidity optimization:

- **Pool Manager Agent**: Liquidity pool management
- **Reservation Agent**: Liquidity reservation optimization
- **Rebalancing Agent**: Automatic pool rebalancing
- **Risk Manager Agent**: Liquidity risk assessment

## 🚀 Getting Started

### Basic Custom Agent

```python
from canza_agents.agents import BaseAgent
from canza_agents.models import PaymentRequest, PaymentResponse

class CustomRouteAgent(BaseAgent):
    """Custom route optimization agent."""
    
    def __init__(self):
        super().__init__(agent_id="custom_router")
        self.optimization_algorithm = "custom_ml_model"
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        # Custom routing logic
        optimized_route = await self._optimize_route(request)
        
        return PaymentResponse(
            payment_id=request.payment_id,
            status="optimized",
            route=optimized_route,
            cost_savings=0.92  # 92% cost reduction
        )
    
    async def _optimize_route(self, request: PaymentRequest):
        # Your custom optimization algorithm
        return {
            "route_id": "custom_route_001",
            "cost": 0.08,  # 8% of traditional cost
            "settlement_time": 1.2,  # 1.2 seconds
            "success_rate": 0.998
        }
```

### Advanced Multi-Agent System

```python
from canza_agents import AgentFramework
from canza_agents.consensus import ConsensusEngine

class AdvancedPaymentSystem:
    """Advanced payment system with custom agents."""
    
    def __init__(self):
        self.framework = AgentFramework()
        self.consensus = ConsensusEngine(threshold=0.8)
        
        # Register custom agents
        self.framework.register_agent(CustomRouteAgent())
        self.framework.register_agent(CustomCostAgent())
        self.framework.register_agent(CustomComplianceAgent())
    
    async def process_payment(self, request: PaymentRequest):
        # Process with consensus
        result = await self.framework.process_with_consensus(request)
        return result
```

## 📁 Examples

### Route Optimization

- `ml_route_agent.py` - Machine learning-based routing
- `cost_aware_router.py` - Cost-optimized routing
- `speed_optimized_router.py` - Speed-optimized routing
- `compliance_router.py` - Compliance-aware routing

### Cost Analysis

- `dynamic_pricing_agent.py` - Dynamic pricing optimization
- `bulk_discount_agent.py` - Volume-based discounts
- `currency_arbitrage_agent.py` - Cross-currency optimization
- `fee_optimization_agent.py` - Fee minimization

### Compliance

- `kyc_agent.py` - KYC verification automation
- `aml_agent.py` - AML screening
- `sanctions_agent.py` - Sanctions checking
- `regulatory_agent.py` - Regulatory compliance

### Liquidity Management

- `pool_manager_agent.py` - Liquidity pool management
- `reservation_agent.py` - Liquidity reservation
- `rebalancing_agent.py` - Pool rebalancing
- `risk_manager_agent.py` - Risk assessment

## 🧪 Testing Custom Agents

### Unit Testing

```python
import pytest
from canza_agents.testing import AgentTestCase

class TestCustomRouteAgent(AgentTestCase):
    async def test_route_optimization(self):
        agent = CustomRouteAgent()
        request = PaymentRequest(amount=1000, currency="USD")
        
        response = await agent.process_payment(request)
        
        assert response.status == "optimized"
        assert response.cost_savings > 0.8
        assert response.route is not None
```

### Integration Testing

```python
class TestCustomAgentIntegration(AgentTestCase):
    async def test_multi_agent_coordination(self):
        system = AdvancedPaymentSystem()
        request = PaymentRequest(amount=5000, currency="EUR")
        
        result = await system.process_payment(request)
        
        assert result.success
        assert result.consensus_reached
        assert result.cost_savings > 0.7
```

## 📊 Performance Monitoring

### Custom Metrics

```python
from canza_agents.monitoring import MetricsCollector

class CustomMetricsAgent(BaseAgent):
    async def process_payment(self, request):
        # Record custom metrics
        await self.metrics.record_custom_metric(
            "custom_optimization_time",
            optimization_time=0.5
        )
        
        # Process payment
        return await super().process_payment(request)
```

### Analytics Dashboard

```python
# Custom analytics
analytics = await metrics.get_custom_analytics()
print(f"Custom optimization success rate: {analytics.custom_success_rate}")
print(f"Average optimization time: {analytics.avg_optimization_time}")
```

## 🔧 Configuration

### Agent Configuration

```python
from canza_agents.config import AgentConfig

config = AgentConfig(
    timeout_seconds=120,  # Longer timeout for complex agents
    retry_attempts=5,     # More retries for reliability
    consensus_threshold=0.8,  # Higher consensus threshold
    enable_custom_metrics=True,
    custom_algorithm_params={
        "ml_model_path": "/models/custom_router.pkl",
        "optimization_weight": 0.7,
        "risk_tolerance": 0.3
    }
)
```

## 📖 Documentation

- [Agent Development Guide](../../docs/sdk/agent-development.md)
- [Custom Agent Patterns](../../docs/sdk/custom-agents.md)
- [Testing Guide](../../docs/sdk/testing.md)
- [Performance Optimization](../../docs/sdk/performance.md)

## 🤝 Contributing

We welcome contributions of new custom agent examples! Please:

1. Create a new agent implementation
2. Add comprehensive tests
3. Include performance benchmarks
4. Document the agent's behavior
5. Follow the project's coding standards

## 📄 License

Custom agent examples are licensed under the MIT License. 