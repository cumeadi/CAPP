
import asyncio
import sys
import os
import uuid
import random
from decimal import Decimal

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Enable Chaos before imports load config
os.environ["CHAOS_ENABLED"] = "true"
os.environ["CHAOS_FAILURE_RATE"] = "0.7" # High failure rate to force retries/failures

from applications.capp.capp.agents.relayer.agent import RelayerAgent, RelayerAgentConfig
from applications.capp.capp.models.payments import (
    CrossBorderPayment, PaymentStatus, SenderInfo, RecipientInfo, 
    Country, Currency, PaymentType, PaymentMethod
)
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.redis import init_redis

async def run_fire_drill():
    print("\n--- 🔥 FIRE DRILL: CHAOS ENGINEERING TEST ---")
    print(f"Chaos Enabled: {os.environ.get('CHAOS_ENABLED')}")
    print(f"Failure Rate: {os.environ.get('CHAOS_FAILURE_RATE')}")
    
    # 0. Init Services
    try:
        await init_redis()
    except Exception as e:
        print(f"Redis init warning: {e}")
    await init_aptos_client()
    
    # 1. Setup Agent with aggressive retry config
    config = RelayerAgentConfig(
        agent_id="relayer-chaos-001",
        retry_attempts=3,      # Retry up to 3 times
        retry_delay=0.5,       # Fast retries for test
        circuit_breaker_enabled=True,
        circuit_breaker_threshold=3, # Open after 3 failures
        circuit_breaker_timeout=5.0
    )
    agent = RelayerAgent(config)
    await agent.start()
    
    # 2. Launch Concurrent Payments
    tasks = []
    for i in range(5):
        tasks.append(submit_payment(agent, i))
        
    results = await asyncio.gather(*tasks)
    
    # 3. Analyze Results
    success_count = sum(1 for r in results if r.success)
    failure_count = sum(1 for r in results if not r.success)
    
    print("\n--- 📊 DRILL RESULTS ---")
    print(f"Total Requests: {len(results)}")
    print(f"Successful: {success_count} ✅")
    print(f"Failed (Chaos/Circuit Breaker): {failure_count} ❌")
    
    if failure_count > 0:
        print("✅ Chaos Monkey successfully injected faults.")
        print("✅ Agent correctly reported failures (or circuit breaker opened).")
    else:
        print("⚠️ No failures occurred? Chaos might be asleep.")

    await agent.stop()

async def submit_payment(agent, index):
    # Dummy Payment Data
    sender = SenderInfo(name="Chaos Tester", phone_number="+000", country=Country.UNITED_STATES)
    recipient = RecipientInfo(name="Target", phone_number="+000", country=Country.UNITED_KINGDOM)
    
    payment = CrossBorderPayment(
        payment_id=str(uuid.uuid4()),
        reference_id=f"CHAOS-{index}-{uuid.uuid4().hex[:4]}",
        payment_type=PaymentType.PERSONAL_REMITTANCE,
        payment_method=PaymentMethod.CRYPTO,
        amount=Decimal("50.00"),
        from_currency=Currency.USDC,
        to_currency=Currency.USDC,
        sender=sender,
        recipient=recipient,
        metadata={
            "target_chain": "Polygon", # Required to bypass same-currency validation
            "route_details": {
                "bridge_provider": "MockBridge",
                "from_chain": "Aptos",
                "to_chain": "Polygon",
                "amount": 50.0,
                "recipient": "0xChaos"
            }
        }
    )
    
    print(f"🚀 Launching Payment {index}...")
    return await agent.process_payment_with_retry(payment)

if __name__ == "__main__":
    asyncio.run(run_fire_drill())
