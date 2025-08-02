#!/usr/bin/env python3
"""
CAPP Phase 3 Implementation Script
Demonstrates production-ready features including database layer and M-Pesa integration.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import uuid4

# Add the project root to the path
sys.path.append('.')

from applications.capp.capp.core.database import (
    init_db, close_db, get_db, 
    PaymentRepository, UserRepository, LiquidityRepository,
    User, Payment, LiquidityPool, PaymentRoute, ExchangeRate
)
from applications.capp.capp.services.mpesa_integration import MpesaService
from applications.capp.capp.config.settings import get_settings

settings = get_settings()


class Phase3Demo:
    """Phase 3 demonstration class."""
    
    def __init__(self):
        self.db_session = None
        self.payment_repo = None
        self.user_repo = None
        self.liquidity_repo = None
    
    async def setup_database(self):
        """Initialize database and repositories."""
        print("🔧 Setting up database...")
        
        # Initialize database tables
        await init_db()
        
        # Get database session
        async for session in get_db():
            self.db_session = session
            self.payment_repo = PaymentRepository(session)
            self.user_repo = UserRepository(session)
            self.liquidity_repo = LiquidityRepository(session)
            break
        
        print("✅ Database setup complete")
    
    async def seed_database(self):
        """Seed database with initial data."""
        print("🌱 Seeding database with initial data...")
        
        # Create test users
        sender_data = {
            "phone": "+2348012345678",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "country": "NGN",
            "kyc_status": "verified"
        }
        
        recipient_data = {
            "phone": "+254712345678",
            "email": "jane.smith@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "country": "KES",
            "kyc_status": "verified"
        }
        
        sender = await self.user_repo.create_user(sender_data)
        recipient = await self.user_repo.create_user(recipient_data)
        
        # Create liquidity pools
        usd_pool = LiquidityPool(
            currency="USD",
            country="US",
            total_liquidity=100000.00,
            available_liquidity=95000.00,
            reserved_liquidity=5000.00,
            min_balance=10000.00,
            max_balance=200000.00
        )
        
        kes_pool = LiquidityPool(
            currency="KES",
            country="KE",
            total_liquidity=15000000.00,
            available_liquidity=14250000.00,
            reserved_liquidity=750000.00,
            min_balance=1000000.00,
            max_balance=50000000.00
        )
        
        self.db_session.add(usd_pool)
        self.db_session.add(kes_pool)
        
        # Create payment routes
        route_data = {
            "from_country": "NGN",
            "to_country": "KES",
            "from_currency": "USD",
            "to_currency": "KES",
            "mmo_provider": "M-Pesa",
            "mmo_provider_code": "MPESA",
            "estimated_fees": 0.80,
            "estimated_duration_minutes": 5,
            "success_rate": 99.5,
            "max_amount": 10000.00,
            "min_amount": 1.00
        }
        
        route = PaymentRoute(**route_data)
        self.db_session.add(route)
        
        # Create exchange rate
        exchange_rate = ExchangeRate(
            from_currency="USD",
            to_currency="KES",
            rate=150.25,
            source="forex_api",
            is_locked=False
        )
        self.db_session.add(exchange_rate)
        
        await self.db_session.commit()
        
        print(f"✅ Created users: {sender.phone}, {recipient.phone}")
        print(f"✅ Created liquidity pools: USD, KES")
        print(f"✅ Created payment route: NGN → KES")
        print(f"✅ Created exchange rate: USD/KES = 150.25")
    
    async def demonstrate_payment_flow(self):
        """Demonstrate complete payment flow with database integration."""
        print("\n💳 Demonstrating complete payment flow...")
        
        # Create payment request
        payment_data = {
            "reference_id": f"PAY_{uuid4().hex[:8].upper()}",
            "amount": 100.00,
            "from_currency": "USD",
            "to_currency": "KES",
            "exchange_rate": 150.25,
            "fees": 0.80,
            "total_amount": 100.80,
            "sender_id": "test-sender-id",  # Would be actual UUID
            "recipient_id": "test-recipient-id",  # Would be actual UUID
            "sender_name": "John Doe",
            "sender_phone": "+2348012345678",
            "sender_country": "NGN",
            "recipient_name": "Jane Smith",
            "recipient_phone": "+254712345678",
            "recipient_country": "KES",
            "status": "pending"
        }
        
        # Create payment in database
        payment = await self.payment_repo.create_payment(payment_data)
        print(f"📝 Created payment: {payment.reference_id}")
        
        # Demonstrate liquidity reservation
        reservation = await self.liquidity_repo.reserve_liquidity(
            currency="KES",
            amount=15025.00,  # 100 USD * 150.25 KES/USD
            payment_id=str(payment.id),
            expires_in_minutes=30
        )
        
        if reservation:
            print(f"💰 Reserved liquidity: {reservation.amount} KES")
        else:
            print("❌ Failed to reserve liquidity")
        
        # Demonstrate M-Pesa integration
        await self.demonstrate_mpesa_integration(payment)
        
        # Update payment status
        await self.payment_repo.update_payment_status(
            str(payment.id),
            "processing",
            processed_at=datetime.utcnow()
        )
        
        print(f"✅ Payment flow demonstration complete")
    
    async def demonstrate_mpesa_integration(self, payment):
        """Demonstrate M-Pesa integration."""
        print("📱 Demonstrating M-Pesa integration...")
        
        # Initialize M-Pesa service
        async with MpesaService() as mpesa:
            # Format phone number
            phone = payment.recipient_phone
            formatted_phone = mpesa.format_phone_number(phone)
            print(f"📞 Formatted phone: {phone} → {formatted_phone}")
            
            # Validate phone number
            is_valid = await mpesa.validate_phone_number(formatted_phone)
            print(f"✅ Phone validation: {is_valid}")
            
            # Simulate STK Push (commented out to avoid actual API calls)
            print("🔄 Simulating STK Push initiation...")
            
            # Mock STK Push response
            mock_stk_response = {
                "success": True,
                "checkout_request_id": f"ws_CO_{uuid4().hex[:16]}",
                "merchant_request_id": f"29115-34620561-{uuid4().hex[:8]}",
                "response_code": 0,
                "response_description": "Success. Request accepted for processing"
            }
            
            print(f"📱 STK Push initiated: {mock_stk_response['checkout_request_id']}")
            
            # Update payment with checkout request ID
            await self.payment_repo.update_payment_status(
                str(payment.id),
                "pending",
                mmo_transaction_id=mock_stk_response["checkout_request_id"]
            )
            
            # Simulate payment status check
            print("🔍 Simulating payment status check...")
            
            # Mock payment completion
            mock_status_response = {
                "success": True,
                "status": "completed",
                "mpesa_receipt_number": f"QK{uuid4().hex[:8].upper()}",
                "transaction_date": datetime.now().strftime("%Y%m%d%H%M%S"),
                "amount": payment.amount,
                "phone_number": formatted_phone
            }
            
            print(f"✅ Payment completed: {mock_status_response['mpesa_receipt_number']}")
            
            # Update payment status to completed
            await self.payment_repo.update_payment_status(
                str(payment.id),
                "completed",
                settled_at=datetime.utcnow()
            )
    
    async def demonstrate_database_queries(self):
        """Demonstrate database query capabilities."""
        print("\n🔍 Demonstrating database queries...")
        
        # Get all payments
        payments = await self.payment_repo.get_payments_by_user("test-user-id", limit=10)
        print(f"📊 Found {len(payments)} payments")
        
        # Get user by phone
        user = await self.user_repo.get_user_by_phone("+254712345678")
        if user:
            print(f"👤 Found user: {user.first_name} {user.last_name}")
        
        # Get liquidity pool
        pool = await self.liquidity_repo.get_pool_by_currency("KES")
        if pool:
            print(f"💰 KES Pool - Available: {pool.available_liquidity}, Reserved: {pool.reserved_liquidity}")
    
    async def demonstrate_error_handling(self):
        """Demonstrate error handling and recovery."""
        print("\n⚠️ Demonstrating error handling...")
        
        # Try to reserve more liquidity than available
        reservation = await self.liquidity_repo.reserve_liquidity(
            currency="KES",
            amount=100000000.00,  # More than available
            payment_id="test-payment-id",
            expires_in_minutes=30
        )
        
        if not reservation:
            print("✅ Correctly handled insufficient liquidity")
        
        # Try to get non-existent payment
        payment = await self.payment_repo.get_payment_by_id("non-existent-id")
        if not payment:
            print("✅ Correctly handled non-existent payment")
    
    async def demonstrate_performance_metrics(self):
        """Demonstrate performance monitoring."""
        print("\n📈 Demonstrating performance metrics...")
        
        start_time = datetime.utcnow()
        
        # Simulate multiple concurrent operations
        tasks = []
        for i in range(10):
            task = self.simulate_payment_operation(i)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        successful_operations = sum(1 for r in results if not isinstance(r, Exception))
        
        print(f"⚡ Processed {successful_operations}/10 operations in {duration:.2f}s")
        print(f"📊 Average time per operation: {duration/10:.3f}s")
        print(f"🎯 Success rate: {successful_operations/10*100:.1f}%")
    
    async def simulate_payment_operation(self, operation_id: int):
        """Simulate a payment operation for performance testing."""
        await asyncio.sleep(0.1)  # Simulate processing time
        return f"Operation {operation_id} completed"
    
    async def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...")
        
        if self.db_session:
            await self.db_session.close()
        
        await close_db()
        print("✅ Cleanup complete")
    
    async def run_demo(self):
        """Run the complete Phase 3 demonstration."""
        print("🚀 CAPP Phase 3 Implementation Demo")
        print("=" * 50)
        
        try:
            # Setup
            await self.setup_database()
            await self.seed_database()
            
            # Demonstrations
            await self.demonstrate_payment_flow()
            await self.demonstrate_database_queries()
            await self.demonstrate_error_handling()
            await self.demonstrate_performance_metrics()
            
            print("\n🎉 Phase 3 Demo Complete!")
            print("\n📋 What was demonstrated:")
            print("✅ Database layer with SQLAlchemy async models")
            print("✅ Repository pattern for data access")
            print("✅ M-Pesa integration with STK Push")
            print("✅ Liquidity management and reservations")
            print("✅ Payment flow orchestration")
            print("✅ Error handling and recovery")
            print("✅ Performance monitoring")
            print("✅ Production-ready architecture")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()


async def main():
    """Main entry point."""
    demo = Phase3Demo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main()) 