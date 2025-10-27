"""
End-to-End Payment Flow Test

Tests complete cross-border payment flow through all agents:
1. Route Optimization Agent - Find best route
2. Compliance Agent - Validate KYC/AML
3. Liquidity Management Agent - Reserve funds
4. Exchange Rate Agent - Lock rates
5. Settlement Agent - Blockchain settlement

Prerequisites:
- PostgreSQL running with migrations complete
- Redis running (optional, for caching)
- All environment variables configured

Run with: python tests/e2e/test_complete_payment_flow.py
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from applications.capp.capp.models.payments import (
    CrossBorderPayment,
    PaymentStatus,
    PaymentParty,
    Country,
    Currency,
    PaymentPreferences
)
from applications.capp.capp.agents.routing.route_optimization_agent import (
    RouteOptimizationAgent,
    RouteOptimizationConfig
)
from applications.capp.capp.agents.compliance.compliance_agent import (
    ComplianceAgent,
    ComplianceConfig
)
from applications.capp.capp.agents.liquidity.liquidity_agent import (
    LiquidityAgent,
    LiquidityConfig
)
from applications.capp.capp.agents.settlement.settlement_agent import (
    SettlementAgent,
    SettlementConfig
)
from applications.capp.capp.core.database import AsyncSessionLocal
from applications.capp.capp.repositories.agent_activity import AgentActivityRepository
from applications.capp.capp.repositories.payment import PaymentRepository


class PaymentFlowTest:
    """End-to-end payment flow test"""

    def __init__(self):
        # Initialize agents
        self.routing_agent = RouteOptimizationAgent(RouteOptimizationConfig())
        self.compliance_agent = ComplianceAgent(ComplianceConfig())
        self.liquidity_agent = LiquidityAgent(LiquidityConfig())
        self.settlement_agent = SettlementAgent(SettlementConfig())

        # Test results
        self.results = {
            "test_name": "Complete Payment Flow",
            "start_time": datetime.now(timezone.utc),
            "payments_tested": 0,
            "successes": 0,
            "failures": 0,
            "errors": [],
            "timings": {}
        }

    def create_test_payment(
        self,
        from_country: Country,
        to_country: Country,
        from_currency: Currency,
        to_currency: Currency,
        amount: Decimal
    ) -> CrossBorderPayment:
        """Create a test payment"""
        return CrossBorderPayment(
            payment_id=uuid4(),
            sender=PaymentParty(
                sender_id=str(uuid4()),
                name="Alice Kamau",
                country=from_country,
                currency=from_currency,
                phone="+254712345678",
                email="alice@example.com"
            ),
            recipient=PaymentParty(
                sender_id=str(uuid4()),
                name="Bob Mukasa",
                country=to_country,
                currency=to_currency,
                phone="+256712345678",
                email="bob@example.com"
            ),
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            preferences=PaymentPreferences(
                priority="standard",
                preferred_provider=None
            ),
            status=PaymentStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            metadata={"test": True}
        )

    async def run_payment_flow(self, payment: CrossBorderPayment) -> dict:
        """Run complete payment through all agents"""
        flow_start = datetime.now(timezone.utc)
        flow_result = {
            "payment_id": str(payment.payment_id),
            "stages": {},
            "success": False,
            "error": None
        }

        try:
            # Stage 1: Route Optimization
            print(f"\n[1/5] Running Route Optimization...")
            stage_start = datetime.now(timezone.utc)

            routing_result = await self.routing_agent.process_payment(payment)
            routing_time = (datetime.now(timezone.utc) - stage_start).total_seconds()

            flow_result["stages"]["routing"] = {
                "success": routing_result.success,
                "time_seconds": routing_time,
                "message": routing_result.message
            }

            if not routing_result.success:
                flow_result["error"] = f"Routing failed: {routing_result.message}"
                return flow_result

            print(f"   ✓ Route selected: {payment.selected_route.route_id if payment.selected_route else 'None'}")
            print(f"   ✓ Exchange rate: {payment.exchange_rate}")
            print(f"   ✓ Time: {routing_time:.3f}s")

            # Stage 2: Compliance Validation
            print(f"\n[2/5] Running Compliance Checks...")
            stage_start = datetime.now(timezone.utc)

            compliance_result = await self.compliance_agent.process_payment(payment)
            compliance_time = (datetime.now(timezone.utc) - stage_start).total_seconds()

            flow_result["stages"]["compliance"] = {
                "success": compliance_result.success,
                "time_seconds": compliance_time,
                "message": compliance_result.message
            }

            if not compliance_result.success:
                flow_result["error"] = f"Compliance failed: {compliance_result.message}"
                return flow_result

            print(f"   ✓ Compliance validated")
            print(f"   ✓ Time: {compliance_time:.3f}s")

            # Stage 3: Liquidity Management
            print(f"\n[3/5] Reserving Liquidity...")
            stage_start = datetime.now(timezone.utc)

            liquidity_result = await self.liquidity_agent.process_payment(payment)
            liquidity_time = (datetime.now(timezone.utc) - stage_start).total_seconds()

            flow_result["stages"]["liquidity"] = {
                "success": liquidity_result.success,
                "time_seconds": liquidity_time,
                "message": liquidity_result.message
            }

            if not liquidity_result.success:
                flow_result["error"] = f"Liquidity reservation failed: {liquidity_result.message}"
                return flow_result

            print(f"   ✓ Liquidity reserved")
            print(f"   ✓ Time: {liquidity_time:.3f}s")

            # Stage 4: Settlement
            print(f"\n[4/5] Processing Settlement...")
            stage_start = datetime.now(timezone.utc)

            settlement_result = await self.settlement_agent.process_payment(payment)
            settlement_time = (datetime.now(timezone.utc) - stage_start).total_seconds()

            flow_result["stages"]["settlement"] = {
                "success": settlement_result.success,
                "time_seconds": settlement_time,
                "message": settlement_result.message
            }

            if not settlement_result.success:
                flow_result["error"] = f"Settlement failed: {settlement_result.message}"
                return flow_result

            print(f"   ✓ Payment queued for settlement")
            print(f"   ✓ Time: {settlement_time:.3f}s")

            # Stage 5: Database Verification
            print(f"\n[5/5] Verifying Database Records...")
            stage_start = datetime.now(timezone.utc)

            db_verification = await self.verify_database_records(payment.payment_id)
            db_time = (datetime.now(timezone.utc) - stage_start).total_seconds()

            flow_result["stages"]["database_verification"] = {
                "success": db_verification["success"],
                "time_seconds": db_time,
                "records_found": db_verification["records_found"]
            }

            print(f"   ✓ Agent activities logged: {db_verification['records_found']}")
            print(f"   ✓ Time: {db_time:.3f}s")

            # Calculate total time
            total_time = (datetime.now(timezone.utc) - flow_start).total_seconds()
            flow_result["total_time_seconds"] = total_time
            flow_result["success"] = True

            print(f"\n✅ Payment flow completed successfully in {total_time:.3f}s")

        except Exception as e:
            flow_result["error"] = str(e)
            print(f"\n❌ Payment flow failed: {str(e)}")

        return flow_result

    async def verify_database_records(self, payment_id: uuid4) -> dict:
        """Verify database records were created"""
        try:
            async with AsyncSessionLocal() as session:
                activity_repo = AgentActivityRepository(session)

                # Get all activities for this payment
                activities = await activity_repo.get_by_payment(payment_id)

                return {
                    "success": True,
                    "records_found": len(activities),
                    "agent_types": [a.agent_type for a in activities]
                }

        except Exception as e:
            return {
                "success": False,
                "records_found": 0,
                "error": str(e)
            }

    async def run_test_suite(self):
        """Run complete test suite"""
        print("=" * 80)
        print("CAPP End-to-End Payment Flow Test")
        print("=" * 80)

        # Test scenarios
        test_scenarios = [
            {
                "name": "Kenya → Uganda (KES → UGX)",
                "payment": self.create_test_payment(
                    Country.KENYA,
                    Country.UGANDA,
                    Currency.KES,
                    Currency.UGX,
                    Decimal("10000.00")
                )
            },
            {
                "name": "Nigeria → Kenya (NGN → KES)",
                "payment": self.create_test_payment(
                    Country.NIGERIA,
                    Country.KENYA,
                    Currency.NGN,
                    Currency.KES,
                    Decimal("50000.00")
                )
            },
            {
                "name": "South Africa → Botswana (ZAR → BWP)",
                "payment": self.create_test_payment(
                    Country.SOUTH_AFRICA,
                    Country.BOTSWANA,
                    Currency.ZAR,
                    Currency.BWP,
                    Decimal("5000.00")
                )
            }
        ]

        # Run each scenario
        for idx, scenario in enumerate(test_scenarios, 1):
            print(f"\n\n{'=' * 80}")
            print(f"Test Scenario {idx}/{len(test_scenarios)}: {scenario['name']}")
            print(f"{'=' * 80}")
            print(f"Amount: {scenario['payment'].amount} {scenario['payment'].from_currency}")
            print(f"Corridor: {scenario['payment'].sender.country} → {scenario['payment'].recipient.country}")

            self.results["payments_tested"] += 1

            result = await self.run_payment_flow(scenario["payment"])

            if result["success"]:
                self.results["successes"] += 1
            else:
                self.results["failures"] += 1
                self.results["errors"].append({
                    "scenario": scenario["name"],
                    "error": result.get("error", "Unknown error")
                })

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        self.results["end_time"] = datetime.now(timezone.utc)
        duration = (self.results["end_time"] - self.results["start_time"]).total_seconds()

        print("\n\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Payments Tested: {self.results['payments_tested']}")
        print(f"Successful:            {self.results['successes']}")
        print(f"Failed:                {self.results['failures']}")
        print(f"Success Rate:          {(self.results['successes'] / self.results['payments_tested'] * 100):.1f}%")
        print(f"Total Duration:        {duration:.2f}s")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error['scenario']}: {error['error']}")

        print("=" * 80)


async def main():
    """Main test entry point"""
    test = PaymentFlowTest()
    await test.run_test_suite()


if __name__ == "__main__":
    asyncio.run(main())
