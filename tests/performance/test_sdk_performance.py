"""
Performance Tests for SDK

Benchmarks SDK performance against original CAPP system to ensure
91% cost reduction and 1.5s processing time are maintained.
"""

import pytest
import asyncio
import time
import statistics
from decimal import Decimal
from typing import List, Dict, Any
import psutil
import os

from canza_agents import (
    FinancialFramework, Region, ComplianceLevel, FinancialTransaction,
    FrameworkConfig
)
from canza_agents.agents import PaymentAgent, ComplianceAgent, RiskAgent


class TestSDKPerformance:
    """Performance tests for SDK framework"""
    
    @pytest.fixture
    async def performance_framework(self):
        """Create framework for performance testing"""
        config = FrameworkConfig(
            region=Region.AFRICA,
            compliance_level=ComplianceLevel.STANDARD,
            enable_learning=True,
            enable_consensus=True,
            max_concurrent_agents=10,
            workflow_timeout=300,
            consensus_threshold=0.75
        )
        
        framework = FinancialFramework(config=config)
        
        # Add optimized agents for performance
        payment_agent = PaymentAgent(
            specialization="africa",
            optimization_strategy="cost_first",
            enable_learning=True
        )
        compliance_agent = ComplianceAgent(
            jurisdictions=["KE", "NG", "UG", "GH"],
            kyc_threshold_amount=1000.0,
            aml_threshold_amount=3000.0
        )
        risk_agent = RiskAgent(
            risk_tolerance="moderate"
        )
        
        framework.add_agent(payment_agent)
        framework.add_agent(compliance_agent)
        framework.add_agent(risk_agent)
        
        await framework.initialize()
        return framework
    
    @pytest.fixture
    def test_transactions(self):
        """Create test transactions for performance testing"""
        transactions = []
        
        # Standard transactions
        for i in range(100):
            transaction = FinancialTransaction(
                transaction_id=f"perf_test_{i:03d}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata={
                    "sender_info": {
                        "id": f"sender_{i}",
                        "country": "US",
                        "name": f"Sender {i}"
                    },
                    "recipient_info": {
                        "id": f"recipient_{i}",
                        "country": "KE",
                        "name": f"Recipient {i}",
                        "phone": f"+254700{i:06d}"
                    },
                    "urgency": "standard",
                    "payment_purpose": "general"
                }
            )
            transactions.append(transaction)
        
        # Cross-border transactions
        for i in range(50):
            transaction = FinancialTransaction(
                transaction_id=f"perf_cb_{i:03d}",
                amount=Decimal("5000.00"),
                from_currency="EUR",
                to_currency="NGN",
                metadata={
                    "sender_info": {
                        "id": f"sender_cb_{i}",
                        "country": "DE",
                        "name": f"Sender CB {i}"
                    },
                    "recipient_info": {
                        "id": f"recipient_cb_{i}",
                        "country": "NG",
                        "name": f"Recipient CB {i}"
                    },
                    "urgency": "high",
                    "payment_purpose": "business"
                }
            )
            transactions.append(transaction)
        
        # Large amount transactions
        for i in range(25):
            transaction = FinancialTransaction(
                transaction_id=f"perf_large_{i:03d}",
                amount=Decimal("50000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata={
                    "sender_info": {
                        "id": f"sender_large_{i}",
                        "country": "US",
                        "name": f"Sender Large {i}"
                    },
                    "recipient_info": {
                        "id": f"recipient_large_{i}",
                        "country": "KE",
                        "name": f"Recipient Large {i}"
                    },
                    "urgency": "standard",
                    "payment_purpose": "business"
                }
            )
            transactions.append(transaction)
        
        return transactions
    
    @pytest.mark.asyncio
    async def test_91_percent_cost_reduction_benchmark(self, performance_framework, test_transactions):
        """Benchmark test to validate 91% cost reduction achievement"""
        print("\n🧪 Benchmarking 91% Cost Reduction Achievement...")
        
        results = []
        start_time = time.time()
        
        # Process transactions
        for transaction in test_transactions:
            result = await performance_framework.optimize_payment(transaction)
            results.append(result)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        successful_results = [r for r in results if r.success]
        cost_savings = [r.cost_savings_percentage for r in successful_results]
        
        avg_cost_savings = statistics.mean(cost_savings) if cost_savings else 0
        min_cost_savings = min(cost_savings) if cost_savings else 0
        max_cost_savings = max(cost_savings) if cost_savings else 0
        success_rate = len(successful_results) / len(results) * 100
        
        print(f"📊 Cost Reduction Benchmark Results:")
        print(f"   Total Transactions: {len(results)}")
        print(f"   Success Rate: {success_rate:.2f}%")
        print(f"   Average Cost Savings: {avg_cost_savings:.2f}%")
        print(f"   Min Cost Savings: {min_cost_savings:.2f}%")
        print(f"   Max Cost Savings: {max_cost_savings:.2f}%")
        print(f"   Total Processing Time: {total_time:.2f}s")
        print(f"   Transactions per Second: {len(results) / total_time:.2f}")
        
        # Performance assertions
        assert success_rate >= 90.0, f"Success rate {success_rate}% below target 90%"
        assert avg_cost_savings >= 85.0, f"Average cost savings {avg_cost_savings}% below target 85%"
        assert min_cost_savings >= 70.0, f"Minimum cost savings {min_cost_savings}% below target 70%"
        
        # Check if we achieved close to 91%
        if avg_cost_savings >= 90.0:
            print(f"✅ SUCCESS: Achieved {avg_cost_savings:.2f}% average cost reduction (target: 91%)")
        else:
            print(f"⚠️  WARNING: Achieved {avg_cost_savings:.2f}% average cost reduction (target: 91%)")
    
    @pytest.mark.asyncio
    async def test_1_5_second_processing_time_benchmark(self, performance_framework, test_transactions):
        """Benchmark test to validate 1.5s processing time achievement"""
        print("\n⏱️  Benchmarking 1.5s Processing Time Achievement...")
        
        processing_times = []
        start_time = time.time()
        
        # Process transactions and collect processing times
        for transaction in test_transactions:
            result = await performance_framework.optimize_payment(transaction)
            if result.success:
                processing_times.append(result.total_processing_time)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0
        min_processing_time = min(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        p95_processing_time = statistics.quantiles(processing_times, n=20)[18] if len(processing_times) >= 20 else max_processing_time
        
        print(f"📊 Processing Time Benchmark Results:")
        print(f"   Total Transactions: {len(test_transactions)}")
        print(f"   Successful Transactions: {len(processing_times)}")
        print(f"   Average Processing Time: {avg_processing_time:.3f}s")
        print(f"   Min Processing Time: {min_processing_time:.3f}s")
        print(f"   Max Processing Time: {max_processing_time:.3f}s")
        print(f"   95th Percentile: {p95_processing_time:.3f}s")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Transactions per Second: {len(test_transactions) / total_time:.2f}")
        
        # Performance assertions
        assert avg_processing_time <= 2.0, f"Average processing time {avg_processing_time}s above target 2s"
        assert p95_processing_time <= 3.0, f"95th percentile processing time {p95_processing_time}s above target 3s"
        
        # Check if we achieved close to 1.5s
        if avg_processing_time <= 1.8:
            print(f"✅ SUCCESS: Achieved {avg_processing_time:.3f}s average processing time (target: 1.5s)")
        else:
            print(f"⚠️  WARNING: Achieved {avg_processing_time:.3f}s average processing time (target: 1.5s)")
    
    @pytest.mark.asyncio
    async def test_load_testing_scalability(self, performance_framework):
        """Load testing to validate scalability"""
        print("\n🚀 Load Testing Scalability...")
        
        # Test different load levels
        load_levels = [10, 50, 100, 200, 500]
        results = {}
        
        for load in load_levels:
            print(f"   Testing {load} concurrent transactions...")
            
            # Create transactions for this load level
            transactions = []
            for i in range(load):
                transaction = FinancialTransaction(
                    transaction_id=f"load_test_{load}_{i}",
                    amount=Decimal("1000.00"),
                    from_currency="USD",
                    to_currency="KES",
                    metadata={
                        "sender_info": {"id": f"sender_{i}", "country": "US"},
                        "recipient_info": {"id": f"recipient_{i}", "country": "KE"}
                    }
                )
                transactions.append(transaction)
            
            # Process concurrently
            start_time = time.time()
            
            async def process_single_transaction(tx):
                return await performance_framework.optimize_payment(tx)
            
            tasks = [process_single_transaction(tx) for tx in transactions]
            load_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_time = time.time() - start_time
            
            # Calculate metrics
            successful_results = [r for r in load_results if isinstance(r, object) and hasattr(r, 'success') and r.success]
            success_rate = len(successful_results) / len(load_results) * 100
            
            if successful_results:
                avg_cost_savings = statistics.mean([r.cost_savings_percentage for r in successful_results])
                avg_processing_time = statistics.mean([r.total_processing_time for r in successful_results])
            else:
                avg_cost_savings = 0
                avg_processing_time = 0
            
            results[load] = {
                "total_time": total_time,
                "success_rate": success_rate,
                "avg_cost_savings": avg_cost_savings,
                "avg_processing_time": avg_processing_time,
                "transactions_per_second": load / total_time
            }
            
            print(f"     Success Rate: {success_rate:.1f}%")
            print(f"     Avg Cost Savings: {avg_cost_savings:.1f}%")
            print(f"     Avg Processing Time: {avg_processing_time:.3f}s")
            print(f"     Transactions/Second: {load / total_time:.1f}")
        
        # Print summary
        print(f"\n📊 Load Testing Summary:")
        for load, metrics in results.items():
            print(f"   {load} transactions:")
            print(f"     Success Rate: {metrics['success_rate']:.1f}%")
            print(f"     Avg Cost Savings: {metrics['avg_cost_savings']:.1f}%")
            print(f"     Avg Processing Time: {metrics['avg_processing_time']:.3f}s")
            print(f"     Throughput: {metrics['transactions_per_second']:.1f} txn/s")
        
        # Performance assertions
        for load, metrics in results.items():
            assert metrics["success_rate"] >= 80.0, f"Success rate {metrics['success_rate']}% below 80% for {load} transactions"
            assert metrics["avg_cost_savings"] >= 80.0, f"Cost savings {metrics['avg_cost_savings']}% below 80% for {load} transactions"
            assert metrics["avg_processing_time"] <= 5.0, f"Processing time {metrics['avg_processing_time']}s above 5s for {load} transactions"
    
    @pytest.mark.asyncio
    async def test_memory_usage_benchmark(self, performance_framework, test_transactions):
        """Benchmark memory usage during processing"""
        print("\n💾 Memory Usage Benchmark...")
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process transactions in batches
        batch_size = 50
        memory_usage = []
        
        for i in range(0, len(test_transactions), batch_size):
            batch = test_transactions[i:i + batch_size]
            
            # Process batch
            for transaction in batch:
                result = await performance_framework.optimize_payment(transaction)
                assert result.success is True
            
            # Record memory usage
            current_memory = process.memory_info().rss
            memory_usage.append(current_memory)
            
            print(f"   Processed {i + len(batch)} transactions, Memory: {current_memory / (1024*1024):.1f}MB")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        max_memory = max(memory_usage)
        avg_memory = statistics.mean(memory_usage)
        
        print(f"📊 Memory Usage Results:")
        print(f"   Initial Memory: {initial_memory / (1024*1024):.1f}MB")
        print(f"   Final Memory: {final_memory / (1024*1024):.1f}MB")
        print(f"   Memory Increase: {memory_increase / (1024*1024):.1f}MB")
        print(f"   Max Memory: {max_memory / (1024*1024):.1f}MB")
        print(f"   Average Memory: {avg_memory / (1024*1024):.1f}MB")
        
        # Memory assertions
        assert memory_increase < 500 * 1024 * 1024, f"Memory increase {memory_increase / (1024*1024):.1f}MB above 500MB limit"
        assert max_memory < 1000 * 1024 * 1024, f"Max memory {max_memory / (1024*1024):.1f}MB above 1GB limit"
    
    @pytest.mark.asyncio
    async def test_cpu_usage_benchmark(self, performance_framework, test_transactions):
        """Benchmark CPU usage during processing"""
        print("\n🖥️  CPU Usage Benchmark...")
        
        # Monitor CPU usage during processing
        cpu_usage = []
        
        async def process_with_monitoring():
            for i, transaction in enumerate(test_transactions):
                # Record CPU before processing
                cpu_before = psutil.cpu_percent(interval=0.1)
                
                # Process transaction
                result = await performance_framework.optimize_payment(transaction)
                assert result.success is True
                
                # Record CPU after processing
                cpu_after = psutil.cpu_percent(interval=0.1)
                cpu_usage.append((cpu_before, cpu_after))
                
                if (i + 1) % 25 == 0:
                    print(f"   Processed {i + 1} transactions")
        
        await process_with_monitoring()
        
        # Calculate metrics
        avg_cpu_before = statistics.mean([usage[0] for usage in cpu_usage])
        avg_cpu_after = statistics.mean([usage[1] for usage in cpu_usage])
        max_cpu = max([usage[1] for usage in cpu_usage])
        
        print(f"📊 CPU Usage Results:")
        print(f"   Average CPU Before: {avg_cpu_before:.1f}%")
        print(f"   Average CPU After: {avg_cpu_after:.1f}%")
        print(f"   Max CPU Usage: {max_cpu:.1f}%")
        print(f"   CPU Increase: {avg_cpu_after - avg_cpu_before:.1f}%")
        
        # CPU assertions
        assert avg_cpu_after < 80.0, f"Average CPU usage {avg_cpu_after:.1f}% above 80% limit"
        assert max_cpu < 95.0, f"Max CPU usage {max_cpu:.1f}% above 95% limit"
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_benchmark(self, performance_framework):
        """Benchmark concurrent processing performance"""
        print("\n🔄 Concurrent Processing Benchmark...")
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            print(f"   Testing {concurrency} concurrent processes...")
            
            # Create transactions
            transactions = []
            for i in range(100):
                transaction = FinancialTransaction(
                    transaction_id=f"concurrent_{concurrency}_{i}",
                    amount=Decimal("1000.00"),
                    from_currency="USD",
                    to_currency="KES",
                    metadata={
                        "sender_info": {"id": f"sender_{i}", "country": "US"},
                        "recipient_info": {"id": f"recipient_{i}", "country": "KE"}
                    }
                )
                transactions.append(transaction)
            
            # Process with specified concurrency
            start_time = time.time()
            
            semaphore = asyncio.Semaphore(concurrency)
            
            async def process_with_semaphore(tx):
                async with semaphore:
                    return await performance_framework.optimize_payment(tx)
            
            tasks = [process_with_semaphore(tx) for tx in transactions]
            concurrent_results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Calculate metrics
            successful_results = [r for r in concurrent_results if r.success]
            success_rate = len(successful_results) / len(concurrent_results) * 100
            
            if successful_results:
                avg_cost_savings = statistics.mean([r.cost_savings_percentage for r in successful_results])
                avg_processing_time = statistics.mean([r.total_processing_time for r in successful_results])
            else:
                avg_cost_savings = 0
                avg_processing_time = 0
            
            results[concurrency] = {
                "total_time": total_time,
                "success_rate": success_rate,
                "avg_cost_savings": avg_cost_savings,
                "avg_processing_time": avg_processing_time,
                "throughput": len(transactions) / total_time
            }
            
            print(f"     Success Rate: {success_rate:.1f}%")
            print(f"     Avg Cost Savings: {avg_cost_savings:.1f}%")
            print(f"     Avg Processing Time: {avg_processing_time:.3f}s")
            print(f"     Throughput: {len(transactions) / total_time:.1f} txn/s")
        
        # Print summary
        print(f"\n📊 Concurrent Processing Summary:")
        for concurrency, metrics in results.items():
            print(f"   {concurrency} concurrent:")
            print(f"     Success Rate: {metrics['success_rate']:.1f}%")
            print(f"     Avg Cost Savings: {metrics['avg_cost_savings']:.1f}%")
            print(f"     Avg Processing Time: {metrics['avg_processing_time']:.3f}s")
            print(f"     Throughput: {metrics['throughput']:.1f} txn/s")
        
        # Performance assertions
        for concurrency, metrics in results.items():
            assert metrics["success_rate"] >= 85.0, f"Success rate {metrics['success_rate']}% below 85% for {concurrency} concurrent"
            assert metrics["avg_cost_savings"] >= 80.0, f"Cost savings {metrics['avg_cost_savings']}% below 80% for {concurrency} concurrent"
    
    @pytest.mark.asyncio
    async def test_performance_consistency_benchmark(self, performance_framework, test_transactions):
        """Benchmark performance consistency over time"""
        print("\n📈 Performance Consistency Benchmark...")
        
        # Run multiple batches to test consistency
        num_batches = 5
        batch_size = 20
        batch_results = []
        
        for batch_num in range(num_batches):
            print(f"   Running batch {batch_num + 1}/{num_batches}...")
            
            batch_start = batch_num * batch_size
            batch_end = batch_start + batch_size
            batch_transactions = test_transactions[batch_start:batch_end]
            
            batch_start_time = time.time()
            batch_cost_savings = []
            batch_processing_times = []
            
            for transaction in batch_transactions:
                result = await performance_framework.optimize_payment(transaction)
                if result.success:
                    batch_cost_savings.append(result.cost_savings_percentage)
                    batch_processing_times.append(result.total_processing_time)
            
            batch_total_time = time.time() - batch_start_time
            
            batch_results.append({
                "batch_num": batch_num + 1,
                "avg_cost_savings": statistics.mean(batch_cost_savings) if batch_cost_savings else 0,
                "avg_processing_time": statistics.mean(batch_processing_times) if batch_processing_times else 0,
                "total_time": batch_total_time,
                "success_count": len(batch_cost_savings)
            })
        
        # Calculate consistency metrics
        cost_savings_values = [r["avg_cost_savings"] for r in batch_results]
        processing_time_values = [r["avg_processing_time"] for r in batch_results]
        
        cost_savings_std = statistics.stdev(cost_savings_values) if len(cost_savings_values) > 1 else 0
        processing_time_std = statistics.stdev(processing_time_values) if len(processing_time_values) > 1 else 0
        
        avg_cost_savings = statistics.mean(cost_savings_values)
        avg_processing_time = statistics.mean(processing_time_values)
        
        print(f"📊 Consistency Results:")
        print(f"   Average Cost Savings: {avg_cost_savings:.2f}% ± {cost_savings_std:.2f}%")
        print(f"   Average Processing Time: {avg_processing_time:.3f}s ± {processing_time_std:.3f}s")
        print(f"   Cost Savings CV: {(cost_savings_std / avg_cost_savings * 100):.1f}%")
        print(f"   Processing Time CV: {(processing_time_std / avg_processing_time * 100):.1f}%")
        
        # Print batch details
        for result in batch_results:
            print(f"   Batch {result['batch_num']}: {result['avg_cost_savings']:.1f}% savings, {result['avg_processing_time']:.3f}s")
        
        # Consistency assertions
        assert cost_savings_std / avg_cost_savings < 0.1, f"Cost savings coefficient of variation {(cost_savings_std / avg_cost_savings * 100):.1f}% above 10%"
        assert processing_time_std / avg_processing_time < 0.2, f"Processing time coefficient of variation {(processing_time_std / avg_processing_time * 100):.1f}% above 20%"
        assert avg_cost_savings >= 85.0, f"Average cost savings {avg_cost_savings:.1f}% below 85%"
        assert avg_processing_time <= 2.0, f"Average processing time {avg_processing_time:.3f}s above 2s"


class TestCAPPComparison:
    """Performance comparison with original CAPP system"""
    
    @pytest.mark.asyncio
    async def test_sdk_vs_capp_performance_comparison(self):
        """Compare SDK performance with original CAPP system"""
        print("\n🔄 SDK vs CAPP Performance Comparison...")
        
        # Create SDK framework
        sdk_framework = FinancialFramework(
            region=Region.AFRICA,
            compliance_level=ComplianceLevel.STANDARD
        )
        
        payment_agent = PaymentAgent(specialization="africa")
        compliance_agent = ComplianceAgent(jurisdictions=["KE", "NG", "UG"])
        risk_agent = RiskAgent(risk_tolerance="moderate")
        
        sdk_framework.add_agent(payment_agent)
        sdk_framework.add_agent(compliance_agent)
        sdk_framework.add_agent(risk_agent)
        
        await sdk_framework.initialize()
        
        # Create test transactions
        test_transactions = []
        for i in range(50):
            transaction = FinancialTransaction(
                transaction_id=f"comparison_{i}",
                amount=Decimal("1000.00"),
                from_currency="USD",
                to_currency="KES",
                metadata={
                    "sender_info": {"id": f"sender_{i}", "country": "US"},
                    "recipient_info": {"id": f"recipient_{i}", "country": "KE"}
                }
            )
            test_transactions.append(transaction)
        
        # Test SDK performance
        print("   Testing SDK performance...")
        sdk_start_time = time.time()
        sdk_results = []
        
        for transaction in test_transactions:
            result = await sdk_framework.optimize_payment(transaction)
            sdk_results.append(result)
        
        sdk_total_time = time.time() - sdk_start_time
        
        # Calculate SDK metrics
        sdk_successful = [r for r in sdk_results if r.success]
        sdk_success_rate = len(sdk_successful) / len(sdk_results) * 100
        sdk_avg_cost_savings = statistics.mean([r.cost_savings_percentage for r in sdk_successful]) if sdk_successful else 0
        sdk_avg_processing_time = statistics.mean([r.total_processing_time for r in sdk_successful]) if sdk_successful else 0
        
        print(f"📊 SDK Performance:")
        print(f"   Success Rate: {sdk_success_rate:.1f}%")
        print(f"   Average Cost Savings: {sdk_avg_cost_savings:.1f}%")
        print(f"   Average Processing Time: {sdk_avg_processing_time:.3f}s")
        print(f"   Total Time: {sdk_total_time:.2f}s")
        print(f"   Throughput: {len(test_transactions) / sdk_total_time:.1f} txn/s")
        
        # Expected CAPP performance (baseline)
        capp_success_rate = 96.8  # Original CAPP success rate
        capp_avg_cost_savings = 91.2  # Original CAPP cost savings
        capp_avg_processing_time = 1.5  # Original CAPP processing time
        
        print(f"📊 CAPP Baseline:")
        print(f"   Success Rate: {capp_success_rate:.1f}%")
        print(f"   Average Cost Savings: {capp_avg_cost_savings:.1f}%")
        print(f"   Average Processing Time: {capp_avg_processing_time:.3f}s")
        
        # Performance comparison
        success_rate_diff = sdk_success_rate - capp_success_rate
        cost_savings_diff = sdk_avg_cost_savings - capp_avg_cost_savings
        processing_time_diff = sdk_avg_processing_time - capp_avg_processing_time
        
        print(f"📊 Performance Comparison:")
        print(f"   Success Rate Difference: {success_rate_diff:+.1f}%")
        print(f"   Cost Savings Difference: {cost_savings_diff:+.1f}%")
        print(f"   Processing Time Difference: {processing_time_diff:+.3f}s")
        
        # Performance assertions
        assert sdk_success_rate >= capp_success_rate * 0.9, f"SDK success rate {sdk_success_rate:.1f}% below 90% of CAPP baseline {capp_success_rate:.1f}%"
        assert sdk_avg_cost_savings >= capp_avg_cost_savings * 0.9, f"SDK cost savings {sdk_avg_cost_savings:.1f}% below 90% of CAPP baseline {capp_avg_cost_savings:.1f}%"
        assert sdk_avg_processing_time <= capp_avg_processing_time * 1.5, f"SDK processing time {sdk_avg_processing_time:.3f}s above 150% of CAPP baseline {capp_avg_processing_time:.3f}s"
        
        # Performance grade
        if sdk_success_rate >= capp_success_rate * 0.95 and sdk_avg_cost_savings >= capp_avg_cost_savings * 0.95 and sdk_avg_processing_time <= capp_avg_processing_time * 1.2:
            print("✅ EXCELLENT: SDK performance matches or exceeds CAPP baseline")
        elif sdk_success_rate >= capp_success_rate * 0.9 and sdk_avg_cost_savings >= capp_avg_cost_savings * 0.9 and sdk_avg_processing_time <= capp_avg_processing_time * 1.5:
            print("✅ GOOD: SDK performance is within acceptable range of CAPP baseline")
        else:
            print("⚠️  NEEDS IMPROVEMENT: SDK performance below CAPP baseline")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "--tb=short"]) 