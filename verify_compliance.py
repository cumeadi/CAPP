import asyncio
import structlog
from decimal import Decimal
from applications.capp.capp.models.payments import CrossBorderPayment, PaymentRoute, Country, Currency, PaymentMethod, PaymentType, SenderInfo, RecipientInfo
from applications.capp.capp.services.compliance import ComplianceService

logger = structlog.get_logger(__name__)

async def verify_compliance_agent():
    print("Verifying Intelligent Compliance Agent...")
    
    service = ComplianceService()
    
    # 1. Test Clear Transaction (Should Pass)
    print("\n--- Test Case 1: Clear Transaction ---")
    clean_payment = CrossBorderPayment(
        reference_id="CLEAN_001",
        payment_type=PaymentType.PERSONAL_REMITTANCE,
        payment_method=PaymentMethod.MOBILE_MONEY,
        amount=Decimal("500.00"),
        from_currency=Currency.USD,
        to_currency=Currency.KES,
        sender=SenderInfo(name="John Doe", phone_number="+1", country=Country.NIGERIA), # Using Nigeria as source
        recipient=RecipientInfo(name="Jane Doe", phone_number="+254", country=Country.KENYA)
    )
    
    result = await service.check_route_compliance(
        route=None, # Route not needed for AI check context
        from_country=Country.NIGERIA,
        to_country=Country.KENYA,
        payment=clean_payment
    )
    
    print(f"Compliance Status: {result.is_compliant}")
    print(f"Reasoning: {result.reasoning}")
    assert result.is_compliant == True
    assert "critical" not in result.reasoning.lower()

    # 2. Test Sanctioned Entity (Should Fail with Fuzzy Match)
    print("\n--- Test Case 2: Sanctioned Entity (Fuzzy Match: 'Osama Bin Ladden') ---")
    sanctioned_payment = CrossBorderPayment(
        reference_id="BAD_001",
        payment_type=PaymentType.BUSINESS_PAYMENT,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=Decimal("10000.00"),
        from_currency=Currency.USD,
        to_currency=Currency.KES,
        sender=SenderInfo(name="Osama Bin Ladden", phone_number="+999", country=Country.NIGERIA),
        recipient=RecipientInfo(name="Unknown", phone_number="+254", country=Country.KENYA)
    )
    
    result = await service.check_route_compliance(
        route=None,
        from_country=Country.NIGERIA,
        to_country=Country.KENYA,
        payment=sanctioned_payment
    )
    
    print(f"Compliance Status: {result.is_compliant}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Violations: {result.violations}")
    
    assert result.is_compliant == False
    assert "Osama" in result.reasoning or "Terrorist" in result.reasoning
    
    # 3. Test Sanctioned Country (Should Fail)
    print("\n--- Test Case 3: Sanctioned Country in Description ---")
    country_payment = CrossBorderPayment(
        reference_id="COUNTRY_001",
        payment_type=PaymentType.BUSINESS_PAYMENT,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=Decimal("1000.00"),
        from_currency=Currency.USD,
        to_currency=Currency.KES,
        sender=SenderInfo(name="Regular Corp", phone_number="+1", country=Country.NIGERIA),
        recipient=RecipientInfo(name="Trader", phone_number="+254", country=Country.KENYA),
        description="Payment for goods from North Korea"
    )
    
    result = await service.check_route_compliance(
        route=None,
        from_country=Country.NIGERIA,
        to_country=Country.KENYA,
        payment=country_payment
    )
    
    print(f"Compliance Status: {result.is_compliant}")
    print(f"Reasoning: {result.reasoning}")
    
    assert result.is_compliant == False
    assert "North Korea" in result.reasoning

    print("\n✅ All Compliance Agent Tests Passed!")

if __name__ == "__main__":
    asyncio.run(verify_compliance_agent())
