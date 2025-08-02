"""
Canza Agent Framework SDK

Simple, powerful developer interface for achieving 91% cost reduction through
intelligent multi-agent orchestration and proven optimization algorithms.

This SDK provides a clean, intuitive interface that abstracts the complexity
of multi-agent systems while preserving the core intelligence that delivers results.
"""

from .framework import (
    FinancialFramework,
    FrameworkConfig,
    Region,
    ComplianceLevel,
    RiskTolerance,
    AgentResult,
    WorkflowResult
)

# Agent Factory
from .agents import (
    PaymentAgent,
    ComplianceAgent,
    RiskAgent,
    AgentSpecialization,
    create_african_payment_agent,
    create_enterprise_compliance_agent,
    create_urgent_payment_agent
)

# Integration Helpers
from .integrations import (
    MobileMoneyBridge,
    AptosSettlement,
    ConfigurationManager,
    AuthenticationManager,
    setup_mobile_money_integration,
    setup_blockchain_integration,
    setup_configuration,
    setup_authentication
)

# Convenience imports for common use cases
from packages.core.agents.financial_base import FinancialTransaction, TransactionResult
from packages.core.agents.templates import (
    OptimizationStrategy,
    ComplianceLevel as TemplateComplianceLevel
)

__version__ = "1.0.0"
__author__ = "Canza Team"
__description__ = "Canza Agent Framework SDK - Achieve 91% cost reduction with intelligent multi-agent orchestration"

__all__ = [
    # Main Framework
    "FinancialFramework",
    "FrameworkConfig",
    
    # Enums and Types
    "Region",
    "ComplianceLevel",
    "RiskTolerance",
    "AgentResult",
    "WorkflowResult",
    
    # Agent Factory
    "PaymentAgent",
    "ComplianceAgent",
    "RiskAgent",
    "AgentSpecialization",
    "create_african_payment_agent",
    "create_enterprise_compliance_agent",
    "create_urgent_payment_agent",
    
    # Integration Helpers
    "MobileMoneyBridge",
    "AptosSettlement",
    "ConfigurationManager",
    "AuthenticationManager",
    "setup_mobile_money_integration",
    "setup_blockchain_integration",
    "setup_configuration",
    "setup_authentication",
    
    # Convenience Imports
    "FinancialTransaction",
    "TransactionResult",
    "OptimizationStrategy",
    "TemplateComplianceLevel",
]

# Quick start example
def quick_start_example():
    """
    Quick start example showing how to achieve 91% cost reduction
    
    Returns:
        str: Example code snippet
    """
    return '''
# Quick Start - Achieve 91% Cost Reduction

import asyncio
from canza_agents import FinancialFramework, Region, ComplianceLevel, FinancialTransaction
from canza_agents.agents import PaymentAgent, ComplianceAgent
from canza_agents.integrations import setup_mobile_money_integration, setup_blockchain_integration
from decimal import Decimal

async def main():
    # Initialize framework for African payments
    framework = FinancialFramework(
        region=Region.AFRICA,
        compliance_level=ComplianceLevel.STANDARD
    )
    
    # Initialize with Redis for caching
    await framework.initialize()
    
    # Add specialized agents
    payment_agent = PaymentAgent(specialization="africa")
    compliance_agent = ComplianceAgent(jurisdictions=["KE", "NG", "UG"])
    
    framework.add_agent(payment_agent)
    framework.add_agent(compliance_agent)
    
    # Setup integrations
    mobile_money = setup_mobile_money_integration()
    blockchain = setup_blockchain_integration()
    
    await mobile_money.initialize()
    await blockchain.initialize()
    
    # Create a transaction
    transaction = FinancialTransaction(
        transaction_id="tx_123",
        amount=Decimal("1000.00"),
        from_currency="USD",
        to_currency="KES",
        metadata={
            "sender_info": {"id": "sender_1", "country": "US"},
            "recipient_info": {"id": "recipient_1", "country": "KE"}
        }
    )
    
    # Optimize payment with 91% cost reduction
    result = await framework.optimize_payment(transaction)
    
    print(f"Cost savings: {result.cost_savings_percentage}%")
    print(f"Compliance score: {result.compliance_score}")
    print(f"Processing time: {result.total_processing_time}s")
    
    # Send payment via mobile money
    payment_result = await mobile_money.send_payment(
        amount=Decimal("1000.00"),
        recipient_phone="+254700000000",
        provider="mpesa"
    )
    
    # Settle on blockchain
    settlement_result = await blockchain.settle_payment(
        payment_id="tx_123",
        amount=Decimal("1000.00"),
        recipient_address="0x123..."
    )
    
    # Get framework analytics
    analytics = await framework.get_framework_analytics()
    print(f"Total cost savings: ${analytics['total_cost_savings']}")

# Run the example
asyncio.run(main())
'''

# Advanced usage example
def advanced_usage_example():
    """
    Advanced usage example showing custom workflows and agents
    
    Returns:
        str: Example code snippet
    """
    return '''
# Advanced Usage - Custom Workflows and Agents

import asyncio
from canza_agents import (
    FinancialFramework, Region, ComplianceLevel, 
    PaymentAgent, ComplianceAgent, FinancialTransaction
)
from canza_agents.integrations import (
    setup_mobile_money_integration, 
    setup_blockchain_integration,
    setup_configuration,
    setup_authentication
)
from decimal import Decimal

async def main():
    # Setup configuration and authentication
    config_manager = setup_configuration("config.json")
    auth_manager = setup_authentication()
    
    # Add credentials
    auth_manager.add_credentials("mpesa", {
        "consumer_key": "your_consumer_key",
        "consumer_secret": "your_consumer_secret",
        "passkey": "your_passkey"
    })
    
    # Initialize framework
    framework = FinancialFramework(region=Region.EAST_AFRICA)
    await framework.initialize()
    
    # Add custom payment agent for cross-border optimization
    payment_agent = PaymentAgent(
        specialization="cross_border",
        optimization_strategy="reliability_first",
        enable_learning=True,
        preferred_providers=["mpesa", "mtn_momo"]
    )
    framework.add_agent(payment_agent)
    
    # Add custom compliance agent for East African jurisdictions
    compliance_agent = ComplianceAgent(
        jurisdictions=["KE", "UG", "TZ", "RW"],
        kyc_threshold_amount=500.0,
        aml_threshold_amount=2000.0,
        alert_on_high_risk=True
    )
    framework.add_agent(compliance_agent)
    
    # Setup integrations
    mobile_money = setup_mobile_money_integration()
    blockchain = setup_blockchain_integration()
    
    await mobile_money.initialize()
    await blockchain.initialize()
    
    # Create custom workflow
    @framework.workflow
    async def cross_border_payment_workflow():
        # Create transaction
        transaction = FinancialTransaction(
            transaction_id="cb_tx_456",
            amount=Decimal("5000.00"),
            from_currency="EUR",
            to_currency="UGX",
            metadata={
                "sender_info": {"id": "sender_2", "country": "DE"},
                "recipient_info": {"id": "recipient_2", "country": "UG"}
            }
        )
        
        # Process through framework
        result = await framework.optimize_payment(transaction)
        
        # Send via mobile money if approved
        if result.success and result.cost_savings_percentage > 50:
            payment_result = await mobile_money.send_payment(
                amount=transaction.amount,
                recipient_phone="+256700000000",
                provider="auto"
            )
            
            # Settle on blockchain
            if payment_result.get("success"):
                settlement_result = await blockchain.settle_payment(
                    payment_id=transaction.transaction_id,
                    amount=transaction.amount,
                    recipient_address="0x456..."
                )
        
        return result
    
    # Execute custom workflow
    result = await cross_border_payment_workflow()
    
    print(f"Workflow success: {result.success}")
    print(f"Consensus reached: {result.consensus_reached}")
    print(f"Cost savings: {result.cost_savings_percentage}%")
    
    # Analyze agent performance
    for agent_result in result.agent_results:
        print(f"Agent {agent_result.agent_type}: {agent_result.confidence} confidence")

# Run the example
asyncio.run(main())
'''

# Integration example
def integration_example():
    """
    Integration example showing mobile money and blockchain usage
    
    Returns:
        str: Example code snippet
    """
    return '''
# Integration Example - Mobile Money and Blockchain

import asyncio
from canza_agents.integrations import (
    setup_mobile_money_integration,
    setup_blockchain_integration,
    setup_configuration,
    setup_authentication
)
from decimal import Decimal

async def main():
    # Setup configuration and authentication
    config_manager = setup_configuration()
    auth_manager = setup_authentication()
    
    # Add service credentials
    auth_manager.add_credentials("mpesa", {
        "consumer_key": "your_consumer_key",
        "consumer_secret": "your_consumer_secret",
        "passkey": "your_passkey"
    })
    
    auth_manager.add_credentials("aptos", {
        "private_key": "your_private_key"
    })
    
    # Setup integrations
    mobile_money = setup_mobile_money_integration()
    blockchain = setup_blockchain_integration()
    
    await mobile_money.initialize()
    await blockchain.initialize()
    
    # Check mobile money provider status
    provider_status = await mobile_money.get_provider_status()
    print("Mobile money providers:", provider_status)
    
    # Send payment via mobile money
    payment_result = await mobile_money.send_payment(
        amount=Decimal("100.00"),
        recipient_phone="+254700000000",
        provider="mpesa"
    )
    
    print(f"Mobile money payment: {payment_result}")
    
    # Check balance
    balance_result = await mobile_money.check_balance(
        phone_number="+254700000000",
        provider="mpesa"
    )
    
    print(f"Balance: {balance_result}")
    
    # Get liquidity pools
    pools = await blockchain.get_liquidity_pools()
    print(f"Liquidity pools: {len(pools)} available")
    
    # Settle payment on blockchain
    settlement_result = await blockchain.settle_payment(
        payment_id="tx_789",
        amount=Decimal("100.00"),
        recipient_address="0x789..."
    )
    
    print(f"Blockchain settlement: {settlement_result}")

# Run the example
asyncio.run(main())
'''

# Export examples for documentation
__examples__ = {
    "quick_start": quick_start_example,
    "advanced_usage": advanced_usage_example,
    "integration": integration_example
} 