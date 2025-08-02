# Quick Start Examples

Basic examples to help you get started with the Canza Platform.

## 🚀 Getting Started

These examples demonstrate the fundamental concepts of the Canza Platform:

### 1. Basic Agent

A simple payment agent that processes basic payment requests.

```python
from canza_agents import AgentFramework
from canza_agents.agents import PaymentAgent

class BasicPaymentAgent(PaymentAgent):
    async def process_payment(self, request):
        # Simple payment processing logic
        return {"status": "completed", "amount": request["amount"]}

# Run the example
python basic_agent.py
```

### 2. Multi-Agent System

Demonstrates coordination between multiple specialized agents.

```python
from canza_agents import AgentFramework
from canza_agents.agents import RouteAgent, CostAgent

# Create and coordinate multiple agents
framework = AgentFramework()
framework.register_agent(RouteAgent())
framework.register_agent(CostAgent())

# Run the example
python multi_agent_system.py
```

### 3. Integration Example

Shows how to integrate with payment systems.

```python
from canza_agents.integrations import MpesaIntegration

# Integrate with M-Pesa
mpesa = MpesaIntegration()
result = await mpesa.send_payment(amount=1000, recipient="254700000000")

# Run the example
python integration_example.py
```

## 📁 Files

- `basic_agent.py` - Simple payment agent
- `multi_agent_system.py` - Multi-agent coordination
- `integration_example.py` - Payment system integration
- `configuration_example.py` - Framework configuration

## 🎯 Next Steps

After running these examples:

1. **Explore the CAPP Reference** - See a complete implementation
2. **Build Custom Agents** - Create your own specialized agents
3. **Read the Documentation** - Deep dive into the platform concepts

## 📖 Documentation

- [Agent Development Guide](../../docs/sdk/agent-development.md)
- [Integration Guide](../../docs/sdk/integrations.md)
- [API Reference](../../docs/sdk/api-reference.md) 