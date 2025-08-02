#!/usr/bin/env python3
"""
Simple Test Script for CAPP

Tests the core components of the CAPP system to ensure everything works correctly.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from applications.capp.capp.services.payment_orchestration import PaymentOrchestrationService
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentStatus, Country, Currency
from applications.capp.capp.agents.liquidity.liquidity_agent import LiquidityAgent, LiquidityConfig
from applications.capp.capp.agents.settlement.settlement_agent import SettlementAgent, SettlementConfig
from applications.capp.capp.agents.compliance.compliance_agent import ComplianceAgent, ComplianceConfig
from applications.capp.capp.agents.exchange.exchange_rate_agent import ExchangeRateAgent, ExchangeRateConfig
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.redis import init_redis


async def initialize_services():
    """Initialize required services for testing"""
    try:
        # Initialize mock Aptos client
        await init_aptos_client()
        print("✅ Aptos client initialized")
        
        # Initialize mock Redis
        await init_redis()
        print("✅ Redis initialized")
        
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        return False


async def test_payment_models():
    """Test payment model creation and validation"""
    print("Testing Payment Models...")
    
    try:
        # Create a test payment
        payment = CrossBorderPayment(
            reference_id="test_payment_001",
            payment_type="personal_remittance",
            payment_method="mobile_money",
            amount=100.00,
            from_currency=Currency.USD,
            to_currency=Currency.KES,
            sender={
                "name": "Test Sender",
                "phone_number": "+1234567890",
                "country": Country.NIGERIA
            },
            recipient={
                "name": "Test Recipient", 
                "phone_number": "+0987654321",
                "country": Country.KENYA
            },
            description="Test payment"
        )
        
        print(f"✅ Payment model created successfully")
        print(f"   Payment ID: {payment.payment_id}")
        print(f"   Amount: {payment.amount} {payment.from_currency}")
        print(f"   Status: {payment.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Payment model test failed: {e}")
        return False


async def test_liquidity_agent():
    """Test liquidity management agent"""
    print("\nTesting Liquidity Agent...")
    
    try:
        config = LiquidityConfig()
        agent = LiquidityAgent(config)
        
        # Test pool status
        pools = await agent.get_all_pools_status()
        print(f"✅ Liquidity agent initialized successfully")
        print(f"   Available pools: {len(pools)}")
        
        # Test liquidity check
        test_payment = CrossBorderPayment(
            reference_id="test_liquidity_001",
            payment_type="personal_remittance",
            payment_method="mobile_money",
            amount=50.00,
            from_currency=Currency.USD,
            to_currency=Currency.KES,
            sender={"name": "Test", "phone_number": "+123", "country": Country.NIGERIA},
            recipient={"name": "Test", "phone_number": "+456", "country": Country.KENYA}
        )
        
        liquidity_result = await agent.check_liquidity_availability(test_payment)
        print(f"   Liquidity check: {'✅ Available' if liquidity_result.success else '❌ Unavailable'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Liquidity agent test failed: {e}")
        return False


async def test_settlement_agent():
    """Test settlement agent"""
    print("\nTesting Settlement Agent...")
    
    try:
        config = SettlementConfig()
        agent = SettlementAgent(config)
        
        print(f"✅ Settlement agent initialized successfully")
        
        # Test queue status
        queue_status = await agent.get_queue_status()
        print(f"   Queue size: {queue_status['queue_size']}")
        print(f"   Pending batches: {queue_status['pending_batches']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Settlement agent test failed: {e}")
        return False


async def test_compliance_agent():
    """Test compliance agent"""
    print("\nTesting Compliance Agent...")
    
    try:
        config = ComplianceConfig()
        agent = ComplianceAgent(config)
        
        print(f"✅ Compliance agent initialized successfully")
        
        # Test analytics
        analytics = await agent.get_compliance_analytics()
        print(f"   Analytics retrieved: {'✅' if analytics else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Compliance agent test failed: {e}")
        return False


async def test_exchange_rate_agent():
    """Test exchange rate agent"""
    print("\nTesting Exchange Rate Agent...")
    
    try:
        config = ExchangeRateConfig()
        agent = ExchangeRateAgent(config)
        
        print(f"✅ Exchange rate agent initialized successfully")
        
        # Test rate sources
        rate_sources = agent.rate_sources
        print(f"   Rate sources: {len(rate_sources)}")
        
        # Test optimal rate calculation
        rate_result = await agent.get_optimal_rate(Currency.USD, Currency.KES)
        print(f"   Optimal rate calculation: {'✅' if rate_result.success else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Exchange rate agent test failed: {e}")
        return False


async def test_payment_orchestration():
    """Test payment orchestration service"""
    print("\nTesting Payment Orchestration...")
    
    try:
        service = PaymentOrchestrationService()
        
        print(f"✅ Payment orchestration service initialized successfully")
        
        # Test analytics
        analytics = await service.get_payment_analytics()
        print(f"   Analytics retrieved: {'✅' if analytics else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Payment orchestration test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("CAPP System Test Suite")
    print("=" * 50)
    
    # Initialize services first
    print("Initializing services...")
    services_initialized = await initialize_services()
    if not services_initialized:
        print("❌ Failed to initialize services. Exiting.")
        return False
    
    print("\nRunning tests...")
    tests = [
        ("Payment Models", test_payment_models),
        ("Liquidity Agent", test_liquidity_agent),
        ("Settlement Agent", test_settlement_agent),
        ("Compliance Agent", test_compliance_agent),
        ("Exchange Rate Agent", test_exchange_rate_agent),
        ("Payment Orchestration", test_payment_orchestration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! CAPP system is ready for demo.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 