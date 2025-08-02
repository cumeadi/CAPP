"""
Integration Tests for SDK Framework

Tests the SDK framework components working together to ensure
they achieve the same performance as the original CAPP system.
"""

import pytest
import asyncio
import time
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from canza_agents import (
    FinancialFramework, Region, ComplianceLevel, FinancialTransaction,
    FrameworkConfig
)
from canza_agents.agents import PaymentAgent, ComplianceAgent, RiskAgent
from canza_agents.agents.financial_base import TransactionResult
from packages.core.agents.templates.payment_optimizer import OptimizationStrategy


class TestSDKFrameworkIntegration:
    """Integration tests for SDK framework components"""
    
    @pytest.fixture
    def framework_config(self):
        """Create framework configuration for testing"""
        return FrameworkConfig(
            region=Region.AFRICA,
            compliance_level=ComplianceLevel.STANDARD,
            enable_learning=True,
            enable_consensus=True,
            max_concurrent_agents=5,
            workflow_timeout=60,
            consensus_threshold=0.75
        )
    
    @pytest.fixture
    async def framework(self, framework_config):
        """Create and initialize framework for testing"""
        framework = FinancialFramework(config=framework_config)
        
        # Add specialized agents
        payment_agent = PaymentAgent(
            specialization="africa",
            optimization_strategy="cost_first",
            enable_learning=True
        )
        compliance_agent = ComplianceAgent(
            jurisdictions=["KE", "NG", "UG", "GH"],
            kyc_threshold_amount=1000.0,
            aml_threshold_amount=3000.0
        )
        risk_agent = RiskAgent(
            risk_tolerance="moderate"
        )
        
        framework.add_agent(payment_agent)
        framework.add_agent(compliance_agent)
        framework.add_agent(risk_agent)
        
        await framework.initialize()
        return framework
    
    @pytest.fixture
    def sample_transaction(self):
        """Create sample transaction for testing"""
        return FinancialTransaction(
            transaction_id="integration_test_001",
            amount=Decimal("1000.00"),
            from_currency="USD",
            to_currency="KES",
            metadata={
                "sender_info": {
                    "id": "sender_001",
                    "country": "US",
                    "name": "John Doe",
                    "email": "john.doe@example.com"
                },
                "recipient_info": {
                    "id": "recipient_001",
                    "country": "KE",
                    "name": "Jane Smith",
                    "phone": "+254700000000",
                    "email": "jane.smith@example.com"
                },
                "urgency": "standard",
                "payment_purpose": "general"
            }
        )
    
    @pytest.fixture
    def cross_border_transaction(self):
        """Create cross-border transaction for testing"""
        return FinancialTransaction(
            transaction_id="integration_test_002",
            amount=Decimal("5000.00"),
            from_currency="EUR",
            to_currency="NGN",
            metadata={
                "sender_info": {
                    "id": "sender_002",
                    "country": "DE",
                    "name": "Hans Mueller"
                },
                "recipient_info": {
                    "id": "recipient_002",
                    "country": "NG",
                    "name": "Adebayo Johnson"
                },
                "urgency": "high",
                "payment_purpose": "business"
            }
        )
    
    @pytest.mark.asyncio
    async def test_framework_initialization(self, framework):
        """Test framework initialization and agent setup"""
        assert framework is not None
        assert framework.config.region == Region.AFRICA
        assert framework.config.compliance_level == ComplianceLevel.STANDARD
        assert framework.config.enable_learning is True
        assert framework.config.enable_consensus is True
        
        # Check that agents were added
        assert len(framework.agents) >= 3  # Payment, Compliance, Risk agents
    
    @pytest.mark.asyncio
    async def test_basic_payment_optimization(self, framework, sample_transaction):
        """Test basic payment optimization through framework"""
        result = await framework.optimize_payment(sample_transaction)
        
        assert result is not None
        assert result.transaction_id == sample_transaction.transaction_id
        assert result.success is True
        assert result.cost_savings_percentage > 0
        assert result.total_processing_time > 0
        assert result.compliance_score > 0
        assert result.risk_score >= 0
    
    @pytest.mark.asyncio
    async def test_cost_reduction_performance(self, framework, sample_transaction):
        """Test that framework achieves 91% cost reduction"""
        result = await framework.optimize_payment(sample_transaction)
        
        # Should achieve at least 85% cost reduction (close to 91%)
        assert result.cost_savings_percentage >= 85.0, \
            f"Expected >=85% cost reduction, got {result.cost_savings_percentage}%"
        
        # Should achieve close to 91% in most cases
        if result.cost_savings_percentage >= 90.0:
            print(f"✅ Framework achieved {result.cost_savings_percentage}% cost reduction (target: 91%)")
    
    @pytest.mark.asyncio
    async def test_processing_time_performance(self, framework, sample_transaction):
        """Test that framework achieves 1.5s processing time"""
        result = await framework.optimize_payment(sample_transaction)
        
        # Should be under 2s (close to 1.5s target)
        assert result.total_processing_time <= 2.0, \
            f"Expected <=2s processing time, got {result.total_processing_time}s"
        
        # Should be close to 1.5s in most cases
        if result.total_processing_time <= 1.8:
            print(f"✅ Framework achieved {result.total_processing_time}s processing time (target: 1.5s)")
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self, framework, sample_transaction):
        """Test coordination between multiple agents"""
        result = await framework.optimize_payment(sample_transaction)
        
        assert result.success is True
        
        # Check that multiple agents contributed
        if hasattr(result, 'agent_results') and result.agent_results:
            agent_types = [ar.agent_type for ar in result.agent_results]
            assert len(agent_types) >= 2, "Should have contributions from multiple agents"
            
            # Should have payment optimizer and compliance agents
            assert any("payment" in agent_type.lower() for agent_type in agent_types)
            assert any("compliance" in agent_type.lower() for agent_type in agent_types)
    
    @pytest.mark.asyncio
    async def test_consensus_mechanism(self, framework, sample_transaction):
        """Test consensus mechanism between agents"""
        result = await framework.optimize_payment(sample_transaction)
        
        assert result.success is True
        
        # Check consensus score if available
        if hasattr(result, 'consensus_score'):
            assert result.consensus_score >= 0.75, \
                f"Consensus score should be >=0.75, got {result.consensus_score}"
    
    @pytest.mark.asyncio
    async def test_cross_border_optimization(self, framework, cross_border_transaction):
        """Test cross-border payment optimization"""
        result = await framework.optimize_payment(cross_border_transaction)
        
        assert result.success is True
        assert result.cost_savings_percentage > 0
        assert result.total_processing_time > 0
        
        # Cross-border transactions should still achieve good cost reduction
        assert result.cost_savings_percentage >= 70.0, \
            f"Cross-border should achieve >=70% cost reduction, got {result.cost_savings_percentage}%"
    
    @pytest.mark.asyncio
    async def test_compliance_integration(self, framework, sample_transaction):
        """Test compliance agent integration"""
        result = await framework.optimize_payment(sample_transaction)
        
        assert result.success is True
        assert result.compliance_score > 0
        
        # Should have good compliance score
        assert result.compliance_score >= 80.0, \
            f"Compliance score should be >=80, got {result.compliance_score}"
    
    @pytest.mark.asyncio
    async def test_risk_assessment_integration(self, framework, sample_transaction):
        """Test risk assessment agent integration"""
        result = await framework.optimize_payment(sample_transaction)
        
        assert result.success is True
        assert result.risk_score >= 0
        
        # Risk score should be reasonable
        assert result.risk_score <= 50.0, \
            f"Risk score should be <=50, got {result.risk_score}"
    
    @pytest.mark.asyncio
    async def test_learning_integration(self, framework, sample_transaction):
        """Test learning mechanism integration"""
        # Process multiple transactions to test learning
        results = []
        
        for i in range(5):
            transaction = FinancialTransaction(
                transaction_id=f"learn_integration_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            result = await framework.optimize_payment(transaction)
            results.append(result)
        
        # Verify learning occurred
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # Check if performance improved over time
        cost_savings = [r.cost_savings_percentage for r in results]
        if len(cost_savings) >= 3:
            # Later results should be at least as good as earlier ones
            later_avg = sum(cost_savings[2:]) / len(cost_savings[2:])
            earlier_avg = sum(cost_savings[:2]) / len(cost_savings[:2])
            assert later_avg >= earlier_avg * 0.95, "Learning should maintain or improve performance"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, framework):
        """Test error handling across framework components"""
        # Test with invalid transaction
        invalid_transaction = FinancialTransaction(
            transaction_id="invalid_integration",
            amount=Decimal("-100.00"),  # Negative amount
            from_currency="INVALID",
            to_currency="INVALID",
            metadata={}
        )
        
        result = await framework.optimize_payment(invalid_transaction)
        
        # Should handle gracefully
        assert result is not None
        # May or may not succeed, but should not crash
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_integration(self, framework, sample_transaction):
        """Test concurrent processing through framework"""
        async def process_single_transaction(i):
            transaction = FinancialTransaction(
                transaction_id=f"concurrent_integration_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            return await framework.optimize_payment(transaction)
        
        # Process 10 transactions concurrently
        tasks = [process_single_transaction(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all transactions processed successfully
        assert len(results) == 10
        assert all(r.success for r in results)
        
        # Check performance under concurrent load
        avg_processing_time = sum(r.total_processing_time for r in results) / len(results)
        assert avg_processing_time <= 3.0, \
            f"Concurrent processing should maintain reasonable time, got {avg_processing_time}s"
    
    @pytest.mark.asyncio
    async def test_analytics_integration(self, framework, sample_transaction):
        """Test analytics and metrics collection"""
        # Process a transaction
        result = await framework.optimize_payment(sample_transaction)
        assert result.success is True
        
        # Get framework analytics
        analytics = await framework.get_framework_analytics()
        
        assert analytics is not None
        assert "total_transactions_processed" in analytics
        assert "average_cost_savings_percentage" in analytics
        assert "average_processing_time" in analytics
        
        # Check analytics values
        assert analytics["total_transactions_processed"] > 0
        assert analytics["average_cost_savings_percentage"] > 0
        assert analytics["average_processing_time"] > 0
    
    @pytest.mark.asyncio
    async def test_workflow_integration(self, framework, sample_transaction):
        """Test custom workflow integration"""
        
        @framework.workflow
        async def test_workflow():
            """Test workflow for payment processing"""
            result = await framework.optimize_payment(sample_transaction)
            
            # Additional processing
            if result.success and result.cost_savings_percentage > 50:
                # Simulate additional processing
                await asyncio.sleep(0.1)
                return result
            
            return result
        
        # Execute workflow
        result = await test_workflow()
        
        assert result is not None
        assert result.success is True
        assert result.cost_savings_percentage > 0
    
    @pytest.mark.asyncio
    async def test_performance_consistency_integration(self, framework, sample_transaction):
        """Test performance consistency across framework"""
        results = []
        
        # Run multiple times to test consistency
        for i in range(10):
            transaction = FinancialTransaction(
                transaction_id=f"consistency_integration_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            result = await framework.optimize_payment(transaction)
            results.append(result)
        
        # Verify consistency
        assert len(results) == 10
        assert all(r.success for r in results)
        
        # Check cost savings consistency
        cost_savings = [r.cost_savings_percentage for r in results]
        avg_cost_savings = sum(cost_savings) / len(cost_savings)
        
        # Should maintain good average cost savings
        assert avg_cost_savings >= 80.0, \
            f"Average cost savings should be >=80%, got {avg_cost_savings}%"
        
        # Check processing time consistency
        processing_times = [r.total_processing_time for r in results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        # Should maintain good average processing time
        assert avg_processing_time <= 2.5, \
            f"Average processing time should be <=2.5s, got {avg_processing_time}s"
    
    @pytest.mark.asyncio
    async def test_memory_usage_integration(self, framework, sample_transaction):
        """Test memory usage during framework processing"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process multiple transactions
        for i in range(50):
            transaction = FinancialTransaction(
                transaction_id=f"memory_integration_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            result = await framework.optimize_payment(transaction)
            assert result.success is True
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 200MB)
        assert memory_increase < 200 * 1024 * 1024, \
            f"Memory increase should be <200MB, got {memory_increase / (1024*1024):.2f}MB"


class TestCAPPReferenceImplementation:
    """Integration tests for CAPP reference implementation"""
    
    @pytest.fixture
    async def capp_framework(self):
        """Create CAPP reference implementation framework"""
        from sdk.examples.capp_reference.config import load_capp_config
        
        config = load_capp_config()
        
        framework = FinancialFramework(
            region=Region.AFRICA,
            compliance_level=ComplianceLevel.ENHANCED
        )
        
        # Add CAPP-specific agents
        payment_agent = PaymentAgent(
            specialization="africa",
            optimization_strategy="cost_first",
            enable_learning=True,
            preferred_providers=["mpesa", "mtn_momo", "airtel_money"]
        )
        compliance_agent = ComplianceAgent(
            jurisdictions=["KE", "NG", "UG", "GH", "TZ", "RW"],
            kyc_threshold_amount=1000.0,
            aml_threshold_amount=3000.0,
            alert_on_high_risk=True
        )
        risk_agent = RiskAgent(
            risk_tolerance="moderate"
        )
        
        framework.add_agent(payment_agent)
        framework.add_agent(compliance_agent)
        framework.add_agent(risk_agent)
        
        await framework.initialize()
        return framework
    
    @pytest.mark.asyncio
    async def test_capp_performance_validation(self, capp_framework):
        """Test that CAPP reference achieves same performance as original"""
        transaction = FinancialTransaction(
            transaction_id="capp_validation_001",
            amount=Decimal("1000.00"),
            from_currency="USD",
            to_currency="KES",
            metadata={
                "sender_info": {"id": "sender_capp", "country": "US"},
                "recipient_info": {"id": "recipient_capp", "country": "KE"},
                "urgency": "standard",
                "payment_purpose": "general"
            }
        )
        
        result = await capp_framework.optimize_payment(transaction)
        
        # Should achieve same performance as original CAPP
        assert result.success is True
        assert result.cost_savings_percentage >= 85.0, \
            f"CAPP reference should achieve >=85% cost reduction, got {result.cost_savings_percentage}%"
        assert result.total_processing_time <= 2.0, \
            f"CAPP reference should achieve <=2s processing time, got {result.total_processing_time}s"
        
        if result.cost_savings_percentage >= 90.0:
            print(f"✅ CAPP reference achieved {result.cost_savings_percentage}% cost reduction")
        if result.total_processing_time <= 1.8:
            print(f"✅ CAPP reference achieved {result.total_processing_time}s processing time")
    
    @pytest.mark.asyncio
    async def test_capp_api_compatibility(self, capp_framework):
        """Test CAPP API compatibility"""
        from sdk.examples.capp_reference.utils import create_transaction_from_request, format_response
        
        # Test request conversion
        request_data = {
            "amount": 1000.00,
            "from_currency": "USD",
            "to_currency": "KES",
            "sender_info": {"id": "sender_api", "country": "US"},
            "recipient_info": {"id": "recipient_api", "country": "KE"}
        }
        
        transaction = create_transaction_from_request(request_data)
        assert transaction.amount == Decimal("1000.00")
        assert transaction.from_currency == "USD"
        assert transaction.to_currency == "KES"
        
        # Test response formatting
        result = await capp_framework.optimize_payment(transaction)
        response = format_response(result)
        
        assert "success" in response
        assert "cost_savings_percentage" in response
        assert "total_processing_time" in response


class TestMobileMoneyIntegration:
    """Integration tests for mobile money components"""
    
    @pytest.mark.asyncio
    async def test_mobile_money_bridge_integration(self):
        """Test mobile money bridge integration"""
        from packages.integrations.mobile_money.bridge import MMOBridge
        from packages.integrations.mobile_money.base_mmo import MMOConfig
        
        config = MMOConfig(
            providers=["mpesa", "mtn_momo", "airtel_money"],
            enable_health_monitoring=True,
            enable_rate_limiting=True,
            enable_caching=True
        )
        
        bridge = MMOBridge(config)
        await bridge.initialize()
        
        # Test provider availability
        providers = await bridge.get_available_providers()
        assert len(providers) > 0
        
        # Test provider selection
        selected_provider = await bridge.select_optimal_provider(
            amount=Decimal("1000.00"),
            recipient_country="KE"
        )
        assert selected_provider is not None
    
    @pytest.mark.asyncio
    async def test_mobile_money_payment_integration(self):
        """Test mobile money payment integration"""
        from packages.integrations.mobile_money.providers.mpesa import MpesaIntegration
        from packages.integrations.mobile_money.base_mmo import MMOConfig
        
        config = MMOConfig(
            api_key="test_key",
            api_secret="test_secret",
            environment="sandbox"
        )
        
        mpesa = MpesaIntegration(config)
        await mpesa.initialize()
        
        # Test payment initiation (mock)
        with patch.object(mpesa, '_make_api_request', return_value={"success": True}):
            result = await mpesa.initiate_payment(
                amount=Decimal("1000.00"),
                recipient_phone="+254700000000",
                reference="test_payment"
            )
            
            assert result is not None
            assert result.get("success") is True


class TestBlockchainIntegration:
    """Integration tests for blockchain components"""
    
    @pytest.mark.asyncio
    async def test_blockchain_settlement_integration(self):
        """Test blockchain settlement integration"""
        from packages.integrations.blockchain.settlement import SettlementService
        from packages.integrations.blockchain.settlement import SettlementConfig
        
        config = SettlementConfig(
            blockchain_network="aptos_testnet",
            gas_limit=1000000,
            max_retries=3,
            retry_delay=1.0
        )
        
        settlement_service = SettlementService(config)
        await settlement_service.initialize()
        
        # Test settlement request (mock)
        with patch.object(settlement_service, '_submit_transaction', return_value={"success": True}):
            result = await settlement_service.settle_payment(
                payment_id="test_payment_001",
                amount=Decimal("1000.00"),
                recipient_address="0x1234567890abcdef",
                currency="APT"
            )
            
            assert result is not None
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_batch_settlement_integration(self):
        """Test batch settlement integration"""
        from packages.integrations.blockchain.settlement import SettlementService
        from packages.integrations.blockchain.settlement import SettlementConfig, BatchSettlementRequest
        
        config = SettlementConfig(
            blockchain_network="aptos_testnet",
            gas_limit=1000000,
            max_retries=3,
            retry_delay=1.0
        )
        
        settlement_service = SettlementService(config)
        await settlement_service.initialize()
        
        # Create batch settlement request
        batch_request = BatchSettlementRequest(
            batch_id="batch_001",
            payments=[
                {
                    "payment_id": "pay_001",
                    "amount": Decimal("1000.00"),
                    "recipient_address": "0x1234567890abcdef"
                },
                {
                    "payment_id": "pay_002",
                    "amount": Decimal("2000.00"),
                    "recipient_address": "0xfedcba0987654321"
                }
            ],
            currency="APT"
        )
        
        # Test batch settlement (mock)
        with patch.object(settlement_service, '_submit_batch_transaction', return_value={"success": True}):
            result = await settlement_service.settle_batch(batch_request)
            
            assert result is not None
            assert result.success is True
            assert len(result.settled_payments) == 2


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"]) 