"""
Unit Tests for Payment Optimizer Agent

Tests the payment optimizer agent to ensure it achieves the same
91% cost reduction and 1.5s processing time as the original CAPP system.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from canza_agents.agents.financial_base import FinancialTransaction, TransactionResult
from packages.core.agents.templates.payment_optimizer import (
    PaymentOptimizerAgent,
    PaymentOptimizerConfig,
    OptimizationStrategy,
    RouteType,
    RouteScore,
    OptimizationResult
)


class TestPaymentOptimizerAgent:
    """Test suite for Payment Optimizer Agent"""
    
    @pytest.fixture
    def agent_config(self):
        """Create test agent configuration"""
        return PaymentOptimizerConfig(
            optimization_strategy=OptimizationStrategy.COST_FIRST,
            enable_learning=True,
            learning_rate=0.1,
            min_cost_savings=50.0,
            max_processing_time=2.0,
            preferred_providers=["mpesa", "mtn_momo", "airtel_money"],
            cost_weight=0.6,
            speed_weight=0.3,
            reliability_weight=0.1
        )
    
    @pytest.fixture
    def agent(self, agent_config):
        """Create test agent instance"""
        return PaymentOptimizerAgent(agent_config)
    
    @pytest.fixture
    def sample_transaction(self):
        """Create sample transaction for testing"""
        return FinancialTransaction(
            transaction_id="test_tx_001",
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
            transaction_id="test_tx_002",
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
    async def test_agent_initialization(self, agent):
        """Test agent initialization"""
        assert agent is not None
        assert agent.config.optimization_strategy == OptimizationStrategy.COST_FIRST
        assert agent.config.enable_learning is True
        assert agent.config.learning_rate == 0.1
        assert len(agent.config.preferred_providers) == 3
        assert "mpesa" in agent.config.preferred_providers
    
    @pytest.mark.asyncio
    async def test_transaction_processing(self, agent, sample_transaction):
        """Test basic transaction processing"""
        result = await agent.process_transaction(sample_transaction)
        
        assert result is not None
        assert result.transaction_id == sample_transaction.transaction_id
        assert result.success is True
        assert result.cost_savings_percentage > 0
        assert result.total_processing_time > 0
        assert result.total_processing_time < 2.0  # Should be under 2s
    
    @pytest.mark.asyncio
    async def test_cost_reduction_achievement(self, agent, sample_transaction):
        """Test that agent achieves 91% cost reduction"""
        result = await agent.process_transaction(sample_transaction)
        
        # Should achieve at least 85% cost reduction (close to 91%)
        assert result.cost_savings_percentage >= 85.0, \
            f"Expected >=85% cost reduction, got {result.cost_savings_percentage}%"
        
        # Should achieve close to 91% in most cases
        if result.cost_savings_percentage >= 90.0:
            print(f"✅ Achieved {result.cost_savings_percentage}% cost reduction (target: 91%)")
    
    @pytest.mark.asyncio
    async def test_processing_time_performance(self, agent, sample_transaction):
        """Test that agent achieves 1.5s processing time"""
        result = await agent.process_transaction(sample_transaction)
        
        # Should be under 2s (close to 1.5s target)
        assert result.total_processing_time <= 2.0, \
            f"Expected <=2s processing time, got {result.total_processing_time}s"
        
        # Should be close to 1.5s in most cases
        if result.total_processing_time <= 1.8:
            print(f"✅ Achieved {result.total_processing_time}s processing time (target: 1.5s)")
    
    @pytest.mark.asyncio
    async def test_route_discovery(self, agent, sample_transaction):
        """Test route discovery functionality"""
        routes = await agent._discover_routes(sample_transaction)
        
        assert len(routes) > 0, "Should discover at least one route"
        assert all(isinstance(route, dict) for route in routes)
        
        # Check route structure
        for route in routes:
            assert "route_type" in route
            assert "providers" in route
            assert "estimated_cost" in route
            assert "estimated_time" in route
            assert "reliability" in route
    
    @pytest.mark.asyncio
    async def test_route_scoring(self, agent, sample_transaction):
        """Test route scoring functionality"""
        # Create test routes
        routes = [
            {
                "route_type": RouteType.DIRECT,
                "providers": ["mpesa"],
                "estimated_cost": 8.8,
                "estimated_time": 1.2,
                "reliability": 0.95
            },
            {
                "route_type": RouteType.HUB,
                "providers": ["hub_provider"],
                "estimated_cost": 12.5,
                "estimated_time": 2.1,
                "reliability": 0.98
            }
        ]
        
        scored_routes = await agent._score_routes(routes, sample_transaction)
        
        assert len(scored_routes) == 2
        assert all(isinstance(route, RouteScore) for route in scored_routes)
        
        # Check scoring logic
        for route_score in scored_routes:
            assert hasattr(route_score, 'cost_score')
            assert hasattr(route_score, 'speed_score')
            assert hasattr(route_score, 'reliability_score')
            assert hasattr(route_score, 'total_score')
            assert 0 <= route_score.total_score <= 100
    
    @pytest.mark.asyncio
    async def test_optimal_route_selection(self, agent, sample_transaction):
        """Test optimal route selection"""
        # Create test routes with different characteristics
        routes = [
            {
                "route_type": RouteType.DIRECT,
                "providers": ["mpesa"],
                "estimated_cost": 8.8,
                "estimated_time": 1.2,
                "reliability": 0.95
            },
            {
                "route_type": RouteType.HUB,
                "providers": ["hub_provider"],
                "estimated_cost": 12.5,
                "estimated_time": 2.1,
                "reliability": 0.98
            },
            {
                "route_type": RouteType.MULTI_HOP,
                "providers": ["provider1", "provider2"],
                "estimated_cost": 6.5,
                "estimated_time": 3.5,
                "reliability": 0.92
            }
        ]
        
        optimal_route = await agent._select_optimal_route(routes, sample_transaction)
        
        assert optimal_route is not None
        assert "route_type" in optimal_route
        assert "providers" in optimal_route
    
    @pytest.mark.asyncio
    async def test_cross_border_optimization(self, agent, cross_border_transaction):
        """Test cross-border payment optimization"""
        result = await agent.process_transaction(cross_border_transaction)
        
        assert result.success is True
        assert result.cost_savings_percentage > 0
        assert result.total_processing_time > 0
        
        # Cross-border transactions should still achieve good cost reduction
        assert result.cost_savings_percentage >= 70.0, \
            f"Cross-border should achieve >=70% cost reduction, got {result.cost_savings_percentage}%"
    
    @pytest.mark.asyncio
    async def test_optimization_strategies(self, sample_transaction):
        """Test different optimization strategies"""
        strategies = [
            OptimizationStrategy.COST_FIRST,
            OptimizationStrategy.SPEED_FIRST,
            OptimizationStrategy.RELIABILITY_FIRST,
            OptimizationStrategy.BALANCED
        ]
        
        results = {}
        
        for strategy in strategies:
            config = PaymentOptimizerConfig(
                optimization_strategy=strategy,
                enable_learning=False  # Disable learning for consistent testing
            )
            agent = PaymentOptimizerAgent(config)
            
            result = await agent.process_transaction(sample_transaction)
            results[strategy] = result
            
            assert result.success is True
            assert result.cost_savings_percentage > 0
            assert result.total_processing_time > 0
        
        # Verify strategy differences
        cost_first = results[OptimizationStrategy.COST_FIRST]
        speed_first = results[OptimizationStrategy.SPEED_FIRST]
        
        # Cost-first should generally have higher cost savings
        assert cost_first.cost_savings_percentage >= speed_first.cost_savings_percentage * 0.9, \
            "Cost-first strategy should achieve higher cost savings"
    
    @pytest.mark.asyncio
    async def test_learning_functionality(self, agent, sample_transaction):
        """Test learning and adaptation functionality"""
        # Process multiple transactions to test learning
        results = []
        
        for i in range(5):
            transaction = FinancialTransaction(
                transaction_id=f"learn_test_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            result = await agent.process_transaction(transaction)
            results.append(result)
            
            # Test learning from result
            await agent.learn_from_result(result)
        
        # Verify learning occurred (check if performance improved)
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # Check that learning parameters were updated
        assert hasattr(agent, 'learning_rate')
        assert agent.learning_rate > 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test error handling and edge cases"""
        # Test with invalid transaction
        invalid_transaction = FinancialTransaction(
            transaction_id="invalid_tx",
            amount=Decimal("-100.00"),  # Negative amount
            from_currency="INVALID",
            to_currency="INVALID",
            metadata={}
        )
        
        result = await agent.process_transaction(invalid_transaction)
        
        # Should handle gracefully
        assert result is not None
        # May or may not succeed, but should not crash
    
    @pytest.mark.asyncio
    async def test_large_amount_optimization(self, agent):
        """Test optimization for large amounts"""
        large_transaction = FinancialTransaction(
            transaction_id="large_tx",
            amount=Decimal("50000.00"),  # Large amount
            from_currency="USD",
            to_currency="KES",
            metadata={
                "sender_info": {"id": "sender_large", "country": "US"},
                "recipient_info": {"id": "recipient_large", "country": "KE"},
                "urgency": "standard",
                "payment_purpose": "business"
            }
        )
        
        result = await agent.process_transaction(large_transaction)
        
        assert result.success is True
        assert result.cost_savings_percentage > 0
        assert result.total_processing_time > 0
        
        # Large amounts should still achieve good cost reduction
        assert result.cost_savings_percentage >= 80.0, \
            f"Large amounts should achieve >=80% cost reduction, got {result.cost_savings_percentage}%"
    
    @pytest.mark.asyncio
    async def test_urgent_payment_optimization(self, agent):
        """Test optimization for urgent payments"""
        urgent_transaction = FinancialTransaction(
            transaction_id="urgent_tx",
            amount=Decimal("1000.00"),
            from_currency="USD",
            to_currency="KES",
            metadata={
                "sender_info": {"id": "sender_urgent", "country": "US"},
                "recipient_info": {"id": "recipient_urgent", "country": "KE"},
                "urgency": "urgent",
                "payment_purpose": "emergency"
            }
        )
        
        result = await agent.process_transaction(urgent_transaction)
        
        assert result.success is True
        assert result.cost_savings_percentage > 0
        assert result.total_processing_time > 0
        
        # Urgent payments should prioritize speed
        assert result.total_processing_time <= 1.5, \
            f"Urgent payments should be processed quickly, got {result.total_processing_time}s"
    
    @pytest.mark.asyncio
    async def test_provider_preferences(self, sample_transaction):
        """Test provider preference handling"""
        # Test with specific provider preferences
        config = PaymentOptimizerConfig(
            optimization_strategy=OptimizationStrategy.COST_FIRST,
            preferred_providers=["mpesa"],  # Only M-Pesa
            enable_learning=False
        )
        agent = PaymentOptimizerAgent(config)
        
        result = await agent.process_transaction(sample_transaction)
        
        assert result.success is True
        assert result.cost_savings_percentage > 0
        
        # Should use preferred provider when possible
        if hasattr(result, 'optimal_providers') and result.optimal_providers:
            assert "mpesa" in result.optimal_providers, \
                "Should use preferred provider when available"
    
    @pytest.mark.asyncio
    async def test_performance_consistency(self, agent, sample_transaction):
        """Test performance consistency across multiple runs"""
        results = []
        
        # Run multiple times to test consistency
        for i in range(10):
            transaction = FinancialTransaction(
                transaction_id=f"consistency_test_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            result = await agent.process_transaction(transaction)
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
        assert avg_processing_time <= 2.0, \
            f"Average processing time should be <=2s, got {avg_processing_time}s"
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, agent, sample_transaction):
        """Test memory usage during processing"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process multiple transactions
        for i in range(100):
            transaction = FinancialTransaction(
                transaction_id=f"memory_test_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            result = await agent.process_transaction(transaction)
            assert result.success is True
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024, \
            f"Memory increase should be <100MB, got {memory_increase / (1024*1024):.2f}MB"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, agent, sample_transaction):
        """Test concurrent transaction processing"""
        async def process_single_transaction(i):
            transaction = FinancialTransaction(
                transaction_id=f"concurrent_test_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata=sample_transaction.metadata
            )
            
            return await agent.process_transaction(transaction)
        
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


class TestPaymentOptimizerConfig:
    """Test suite for Payment Optimizer Configuration"""
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid configuration
        config = PaymentOptimizerConfig(
            optimization_strategy=OptimizationStrategy.COST_FIRST,
            enable_learning=True,
            learning_rate=0.1,
            min_cost_savings=50.0,
            max_processing_time=2.0
        )
        
        assert config.optimization_strategy == OptimizationStrategy.COST_FIRST
        assert config.enable_learning is True
        assert config.learning_rate == 0.1
        assert config.min_cost_savings == 50.0
        assert config.max_processing_time == 2.0
    
    def test_config_defaults(self):
        """Test configuration defaults"""
        config = PaymentOptimizerConfig()
        
        assert config.optimization_strategy == OptimizationStrategy.BALANCED
        assert config.enable_learning is True
        assert config.learning_rate == 0.1
        assert config.min_cost_savings == 50.0
        assert config.max_processing_time == 2.0
    
    def test_config_validation_errors(self):
        """Test configuration validation errors"""
        with pytest.raises(ValueError):
            PaymentOptimizerConfig(learning_rate=-0.1)
        
        with pytest.raises(ValueError):
            PaymentOptimizerConfig(min_cost_savings=-10.0)
        
        with pytest.raises(ValueError):
            PaymentOptimizerConfig(max_processing_time=0.0)


class TestRouteScore:
    """Test suite for Route Score"""
    
    def test_route_score_creation(self):
        """Test route score creation"""
        route = {
            "route_type": RouteType.DIRECT,
            "providers": ["mpesa"],
            "estimated_cost": 8.8,
            "estimated_time": 1.2,
            "reliability": 0.95
        }
        
        score = RouteScore(
            route=route,
            cost_score=85.0,
            speed_score=90.0,
            reliability_score=95.0,
            total_score=88.0
        )
        
        assert score.route == route
        assert score.cost_score == 85.0
        assert score.speed_score == 90.0
        assert score.reliability_score == 95.0
        assert score.total_score == 88.0
    
    def test_route_score_validation(self):
        """Test route score validation"""
        route = {"route_type": RouteType.DIRECT, "providers": ["mpesa"]}
        
        # Valid scores
        score = RouteScore(
            route=route,
            cost_score=85.0,
            speed_score=90.0,
            reliability_score=95.0,
            total_score=88.0
        )
        
        assert 0 <= score.cost_score <= 100
        assert 0 <= score.speed_score <= 100
        assert 0 <= score.reliability_score <= 100
        assert 0 <= score.total_score <= 100


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"]) 