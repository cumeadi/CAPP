
import asyncio
import sys
import os
import uuid
from decimal import Decimal

# Fix path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from applications.capp.capp.agents.relayer.agent import RelayerAgent, RelayerAgentConfig
from applications.capp.capp.models.payments import (
    CrossBorderPayment, PaymentStatus, SenderInfo, RecipientInfo, 
    Country, Currency, PaymentType, PaymentMethod
)
from applications.capp.capp.core.aptos import init_aptos_client
from applications.capp.capp.core.redis import init_redis


async def test_relayer_agent():
    print("\n--- TEST: RELAYER AGENT ORCHESTRATION ---")
    
    # 0. Init Mock Services
    try:
        await init_redis()
    except Exception as e:
        print(f"Redis init warning: {e}")
    
    await init_aptos_client()
    
    # 1. Setup Agent
    config = RelayerAgentConfig(agent_id="relayer-001")
    agent = RelayerAgent(config)
    await agent.start()
    
    # 2. Create Dummy Payment with Full Schema
    sender = SenderInfo(
        name="Alice Test",
        phone_number="+15550101",
        country=Country.UNITED_STATES,
        city="New York"
    )
    
    recipient = RecipientInfo(
        name="Bob Test",
        phone_number="+525550102",
        country=Country.SOUTH_AFRICA, # Using ZA for consistency with RecipientInfo
        address="123 Capetown St"
    )

    payment_id = str(uuid.uuid4())
    payment = CrossBorderPayment(
        payment_id=payment_id,
        reference_id=f"REF-{uuid.uuid4().hex[:8]}",
        payment_type=PaymentType.PERSONAL_REMITTANCE,
        payment_method=PaymentMethod.CRYPTO,
        amount=Decimal("75.00"),
        from_currency=Currency.USDC,
        to_currency=Currency.USDC, # Can be same for bridging
        sender=sender,
        recipient=recipient,
        metadata={
            "route_details": {
                "bridge_provider": "MockBridge",
                "from_chain": "Aptos",
                "to_chain": "Polygon",
                "amount": 75.0,
                "recipient": "0xRecipientWallet"
            },
            "target_chain": "Polygon" # Metadata hint for validation
        }
    )
    
    print(f"🤖 Agent {agent.agent_id} processing {payment.reference_id}...")
    
    # 3. Process
    result = await agent.process_payment_with_retry(payment)
    
    # 4. Verify
    if result.success:
        print("✅ Agent Execution Successful")
        print(f"   Tx Hash: {result.transaction_hash}")
        print(f"   Message: {result.message}")
    else:
        print(f"❌ Agent Execution Failed: {result.message}")
        print(f"   Error Code: {result.error_code}")
        
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(test_relayer_agent())
