import asyncio
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime, timezone

# Add CAPP root to path
sys.path.append(os.getcwd())

# Mock google.generativeai to avoid environment issues
sys.modules["google.generativeai"] = MagicMock()
sys.modules["google.generativeai.types"] = MagicMock()

# Mock Settings and Redis before imports
with patch("applications.capp.capp.config.settings.get_settings") as mock_settings, \
     patch("applications.capp.capp.core.redis.get_cache") as mock_cache, \
     patch("applications.capp.capp.core.aptos.get_aptos_client") as mock_aptos, \
     patch("applications.capp.capp.core.redis.get_redis_client") as mock_redis_client:
    
    # Mock Settings Attributes
    mock_settings.return_value.GEMINI_API_KEY = "mock_key"
    mock_settings.return_value.GEMINI_MODEL = "gemini-pro"
    
    # Mock Redis
    mock_redis_instance = AsyncMock()
    mock_cache.return_value = mock_redis_instance
    mock_redis_client.return_value = mock_redis_instance
    
    # Mock Aptos
    mock_aptos.return_value = MagicMock()

    from applications.capp.capp.agents.liquidity.liquidity_agent import LiquidityAgent, LiquidityConfig
    from applications.capp.capp.agents.compliance.compliance_agent import ComplianceAgent, ComplianceConfig
    from applications.capp.capp.models.payments import CrossBorderPayment, PaymentType, PaymentMethod, Currency, Country, SenderInfo, RecipientInfo

async def verify_autonomous_brain():
    print("🧠 Verifying Autonomous Brain Integration...\n")
    
    # --- TEST 1: Liquidity Agent with Market Brain ---
    print("--- Test 1: Liquidity Agent with Market Brain ---")
    
    # Mock Market Analyst
    with patch("applications.capp.capp.agents.liquidity.liquidity_agent.MarketAnalysisAgent") as MockAnalyst:
        mock_analyst_instance = MockAnalyst.return_value
        
        # Scenario: HIGH RISK Market
        mock_analyst_instance.analyze_settlement_risk = AsyncMock(return_value={
            "risk_level": "HIGH",
            "recommendation": "HOLD and INCREASE BUFFERS",
            "reasoning": "Market is extremely volatile due to mocked event."
        })
        
        # Initialize Agent
        config = LiquidityConfig(agent_id="liq_001", agent_type="liquidity")
        agent = LiquidityAgent(config)
        
        # Override Strategy history to force evaluation
        # Inject some history so average is meaningful 
        # Base buffer is 50,000. 
        # Let's say we have a pool with 40,000 available.
        # If risk is HIGH (multiplier 1.5), threshold should be 50,000 * 1.5 = 75,000.
        # Since 40,000 < 75,000, it should trigger rebalance.
        
        pool = agent.liquidity_pools.get("pool_kes_ugx") # Default pool
        pool.available_liquidity = Decimal("40000.00") # Below base buffer
        
        print(f"Initial Pool Balance: {pool.available_liquidity}")
        
        # Run Rebalance
        await agent._rebalance_pool(pool, "periodic_check")
        
        # Verify Market Analyst was consulted
        mock_analyst_instance.analyze_settlement_risk.assert_called_once()
        print("✅ Market Analysis Consulted")
        
        # Verify Result - Since logic is internal, we check logs or state impact
        # Ideally we'd mock the strategy.evaluate_with_ai to assert calls, but checking side effects is better
        # If rebalance triggered, available liquidity should have increased (simulated swap adds amount)
        # Verify pool status or mock calls
        
        print(f"Final Pool Balance: {pool.available_liquidity}")
        if pool.available_liquidity > Decimal("40000.00"):
            print(f"✅ Rebalancing Triggered (Balance increased to {pool.available_liquidity})")
        else:
            print("❌ Rebalancing NOT Triggered (Unexpected)")

    # --- TEST 2: Compliance Agent with AI Review ---
    print("\n--- Test 2: Compliance Agent with AI Review ---")
    
    # Mock Compliance Services
    with patch("applications.capp.capp.agents.compliance.compliance_agent.ComplianceService") as MockCompService, \
         patch("applications.capp.capp.agents.compliance.compliance_agent.SanctionsService") as MockSanctions, \
         patch("applications.capp.capp.agents.compliance.compliance_agent.FraudDetectionService") as MockFraud, \
         patch("applications.capp.capp.agents.compliance.compliance_agent.AIComplianceAgent") as MockAIAgent:
             
        # Setup Standard Checks Failure (e.g. Sanctions Hit)
        mock_sanctions_instance = MockSanctions.return_value
        mock_sanctions_instance.screening_check = AsyncMock(return_value={
            "is_sanctioned": True,
            "reason": "Mock Sanction Hit"
        })
        
        # Setup AI Overrule
        mock_ai_instance = MockAIAgent.return_value
        mock_ai_instance.evaluate_transaction = AsyncMock(return_value={
            "is_compliant": True,
            "risk_score": 0.2,
            "reasoning": "False Positive: Name match is coincidental."
        })
        
        # Initialize Agent
        comp_config = ComplianceConfig(agent_id="comp_001", agent_type="compliance")
        comp_agent = ComplianceAgent(comp_config)
        
        # Create Payment
        payment = CrossBorderPayment(
            reference_id="TEST_AI_001",
            payment_type=PaymentType.PERSONAL_REMITTANCE,
            payment_method=PaymentMethod.MOBILE_MONEY,
            amount=Decimal("1000.00"),
            from_currency=Currency.USD,
            to_currency=Currency.KES,
            sender=SenderInfo(name="Osama Smith", phone_number="+1", country=Country.NIGERIA),
            recipient=RecipientInfo(name="Jane Doe", phone_number="+254", country=Country.KENYA)
        )
        
        # Run Validation
        result = await comp_agent.validate_payment_compliance(payment)
        
        # Verify Results
        print(f"Compliance Result: {result.is_compliant}")
        print(f"Risk Level: {result.risk_level}")
        print(f"Checks Performed: {[c.check_type for c in result.checks]}")
        
        found_ai_check = False
        for check in result.checks:
            if check.check_type == "ai_review":
                print(f"AI Review Reasoning: {check.details.get('reasoning')}")
                found_ai_check = True
        
        if found_ai_check and result.is_compliant:
            print("✅ AI Autonomous Review Triggered and Overrode Failure")
        else:
            print("❌ AI Review Failed or Did Not Override")

if __name__ == "__main__":
    asyncio.run(verify_autonomous_brain())
