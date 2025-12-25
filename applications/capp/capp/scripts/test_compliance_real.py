import asyncio
import sys
import os
import uuid
from decimal import Decimal

# Add path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from applications.capp.capp.agents.compliance.compliance_agent import ComplianceAgent, ComplianceConfig
from applications.capp.capp.models.payments import (
    CrossBorderPayment, SenderInfo, RecipientInfo, 
    PaymentType, PaymentMethod, Country, Currency
)
from applications.capp.capp.core.redis import init_redis
from applications.capp.capp.core.aptos import init_aptos_client

async def compliance_test():
    print("\n🕵️  Starting REAL Compliance Verification...\n")
    
    # Initialize Core Services
    try:
        await init_redis()
    except Exception as e:
        print(f"⚠️ Redis init warning: {e}")
        
    try:
        await init_aptos_client()
    except Exception as e:
        print(f"⚠️ Aptos init warning: {e}")
    
    config = ComplianceConfig()
    agent = ComplianceAgent(config)
    
    # Helper to create payment
    def create_payment(id_suffix, amount, sender_name, sender_country=Country.KENYA):
        return CrossBorderPayment(
            payment_id=str(uuid.uuid4()),
            reference_id=f"REF-{id_suffix}",
            payment_type=PaymentType.PERSONAL_REMITTANCE,
            payment_method=PaymentMethod.BANK_TRANSFER,
            amount=Decimal(str(amount)),
            from_currency=Currency.USD,
            to_currency=Currency.KES,
            sender=SenderInfo(
                name=sender_name, 
                country=sender_country, 
                phone_number="+1234567890",
                sender_id=str(uuid.uuid4())
            ),
            recipient=RecipientInfo(
                name="Innocent Person", 
                country=Country.KENYA,
                phone_number="+254700000000",
                recipient_id=str(uuid.uuid4())
            )
        )

    # Test 1: Sanctioned Entity (Exact Match)
    print("Test 1: Sanctioned Name (Exact Match)")
    try:
        # Osama bin Laden from Somalia (high risk + name match)
        payment = create_payment("sanction_1", 100.00, "Osama bin Laden", Country.SOMALIA)
        result = await agent.process_payment(payment)
        
        if not result.success:
             print(f"✅ BLOCKED successfully: {result.message}")
        else:
             print(f"❌ FAILED to block: {result.message}")
    except Exception as e:
        print(f"❌ Error in Test 1: {e}")

    # Test 2: Sanctioned Entity (Fuzzy Match)
    print("\nTest 2: Sanctioned Name (Fuzzy Match - 'Usama bin Ladin')")
    try:
        payment = create_payment("sanction_2", 100.00, "Usama bin Ladin", Country.SOMALIA)
        result = await agent.process_payment(payment)
        
        if not result.success:
             print(f"✅ BLOCKED successfully: {result.message}")
        else:
             print(f"❌ FAILED to block: {result.message}")
    except Exception as e:
        print(f"❌ Error in Test 2: {e}")

    # Test 3: Structuring Detection ($9900)
    print("\nTest 3: Structuring Detection ($9,900)")
    try:
        payment = create_payment("structuring_1", 9900.00, "Shady Guy", Country.NIGERIA)
        result = await agent.process_payment(payment)
        
        if not result.success:
             print(f"✅ BLOCKED/FLAGGED: {result.message}")
        else:
             print(f"⚠️  Allowed (Check logs for Flags): {result.message}")
             # We expect this to pass risk check but log warnings unless velocity limit is hit
    except Exception as e:
        print(f"❌ Error in Test 3: {e}")
         
    print("\n✅ Compliance Verification Complete.")

if __name__ == "__main__":
    asyncio.run(compliance_test())
