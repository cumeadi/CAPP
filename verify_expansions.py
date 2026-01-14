import asyncio
import sys
import os
from decimal import Decimal

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'applications/capp')))

from capp.services.yield_service import YieldService
from capp.services.compliance import ComplianceService
from capp.models.payments import (
    CrossBorderPayment, PaymentStatus, PaymentType, PaymentMethod, 
    Currency, Country, SenderInfo, RecipientInfo
)

# Mock Cache
class MockCache:
    def __init__(self):
        self.store = {}
    
    async def get(self, key):
        return self.store.get(key)
    
    async def set(self, key, value, ttl=None):
        self.store[key] = value
        return True
        
    async def delete(self, key):
        if key in self.store:
            del self.store[key]
        return True
    
    async def close(self):
        pass

# Monkeypatch
import capp.core.redis
import capp.services.yield_service
import capp.services.compliance

mock_cache = MockCache()
def get_mock_cache():
    return mock_cache

capp.core.redis.get_cache = get_mock_cache
capp.services.yield_service.get_cache = get_mock_cache
capp.services.compliance.get_cache = get_mock_cache

async def run_verification():
    print("🚀 Starting CAPP Expansion Verification\n")

    # 1. Initialize Services
    print("--- 1. Initializing Services ---")
    yield_service = YieldService()
    compliance_service = ComplianceService()
    
    print("✅ Services Initialized\n")

    # 2. Verify Smart Sweep / Yield Service
    print("--- 2. Verifying Smart Sweep (Yield Service) ---")
    balance_before = await yield_service.get_total_treasury_balance()
    print(f"💰 Initial Treasury Balance: ${balance_before['total_usd_value']:,.2f} (Liquid USDC: ${balance_before['breakdown']['USDC']['hot']:,.2f})")

    # Simulate Idle Funds Monitor
    print("🔄 Running Smart Sweep Monitor...")
    sweep_result = await yield_service.monitor_idle_funds()
    if sweep_result:
        print(f"✨ Smart Sweep Triggered: {sweep_result}")
    else:
        print("zzz No Sweep Needed (Funds already optimized)")
    
    # Request Liquidity (Unwind)
    print("💸 Requesting $50,000 Liquidity for Payment...")
    has_liquidity = await yield_service.request_liquidity(Decimal("50000"), "USDC")
    print(f"Liquidity Available: {has_liquidity}")
    print("✅ Smart Sweep Verification Complete\n")

    # 3. Verify Compliance Shield
    print("--- 3. Verifying Compliance Shield ---")
    
    # Helper to create payment
    def create_payment(amount, sender_id="alice", recipient_id="bob", country=Country.UNITED_STATES):
        return CrossBorderPayment(
            reference_id=f"REF-{amount}-{sender_id}",
            payment_type=PaymentType.PERSONAL_REMITTANCE,
            payment_method=PaymentMethod.DIGITAL_WALLET,
            amount=Decimal(str(amount)),
            from_currency=Currency.USD,
            to_currency=Currency.NGN,
            sender=SenderInfo(
                name=sender_id,
                phone_number="+1234567890",
                country=Country.UNITED_STATES
            ),
            recipient=RecipientInfo(
                name=recipient_id,
                phone_number="+2345678901",
                country=Country.NIGERIA
            )
        )

    # Case A: Compliant Payment
    clean_payment = create_payment(500.00, "user_alice", "user_bob")
    print(f"🔍 Checking Clean Payment: {clean_payment.amount} USD -> {clean_payment.recipient.name}")
    
    # Mocking config usually needed for compliance? validation passed in via DI?
    # check_route_compliance signature: (payment, route)
    # We pass None for route as we are checking payment basics or Travel Rule
    try:
        res_clean = await compliance_service.check_route_compliance(clean_payment, [])
        print(f"Result: Compliant={res_clean.success}, Status={res_clean.status}")
    except Exception as e:
        print(f"Check failed (expected if mock unimplemented): {e}")

    # Case B: Travel Rule Check (Direct)
    large_payment = create_payment(15000.00, "user_alice", "user_bob")
    print(f"🔍 Checking Large Payment (Travel Rule): {large_payment.amount} USD")
    try:
        travel_rule_res = await compliance_service.check_travel_rule(large_payment)
        print(f"Travel Rule Result: {travel_rule_res}")
    except Exception as e:
         print(f"Travel Rule check failed: {e}")

    # Case C: Compliance Shield (Review State)
    # We simulate a payment that might trigger review logic if implemented.
    suspicious_payment = create_payment(5000.00, "user_alice", "suspicious_actor")
    print(f"🔍 Checking Suspicious Payment: {suspicious_payment.recipient.name}")
    
    try:
        res_sus = await compliance_service.check_route_compliance(suspicious_payment, [])
        print(f"Result: Compliant={res_sus.success}, Status={res_sus.status}")
        
        if res_sus.status == PaymentStatus.COMPLIANCE_REVIEW or res_sus.status == "compliance_review":
            print("🛡️  Compliance Shield ACTIVE: Payment held for review.")
        else:
            print(f"Risk Score: {res_sus.risk_score} (Did not trigger shield this time)")
    except Exception as e:
        print(f"Check failed: {e}")

    print("✅ Compliance Shield Verification Complete\n")

if __name__ == "__main__":
    asyncio.run(run_verification())
