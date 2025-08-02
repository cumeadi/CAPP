"""
CAPP Reference Implementation Performance Validation

Tests that validate the reference implementation achieves the same
91% cost reduction and performance benchmarks as the original CAPP system.
"""

import asyncio
import time
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
import json

from canza_agents import FinancialFramework, Region, ComplianceLevel, FinancialTransaction
from canza_agents.agents import PaymentAgent, ComplianceAgent, RiskAgent

from .config import CAPPConfig, load_capp_config, validate_config
from .utils import create_benchmark_transactions, calculate_performance_metrics
from .main import create_capp_reference_system


class PerformanceValidator:
    """
    Performance Validator
    
    Validates that the CAPP reference implementation achieves
    the same performance benchmarks as the original CAPP system.
    """
    
    def __init__(self, config: CAPPConfig):
        self.config = config
        self.framework = None
        self.results = []
        self.validation_results = {}
        
        # Performance targets (matching original CAPP)
        self.targets = {
            "cost_reduction": 91.0,
            "processing_time": 1.5,
            "success_rate": 95.0,
            "compliance_rate": 100.0,
            "consensus_rate": 90.0
        }
    
    async def initialize(self):
        """Initialize the performance validator"""
        try:
            # Create CAPP reference system
            capp_app = create_capp_reference_system(self.config)
            await capp_app.initialize()
            
            # Get framework for direct testing
            self.framework = capp_app.framework
            
            print("✅ Performance Validator initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize Performance Validator: {e}")
            raise
    
    async def run_benchmark_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive benchmark tests
        
        Returns:
            Dict: Benchmark results
        """
        print("🚀 Starting Performance Benchmark Tests")
        print("=" * 50)
        
        # Create benchmark transactions
        transactions = create_benchmark_transactions()
        
        # Run tests
        results = []
        processing_times = []
        cost_savings = []
        success_count = 0
        
        for i, tx_data in enumerate(transactions):
            print(f"📊 Processing transaction {i+1}/{len(transactions)}: {tx_data['payment_id']}")
            
            # Create transaction
            transaction = FinancialTransaction(
                transaction_id=tx_data["payment_id"],
                amount=tx_data["amount"],
                from_currency=tx_data["from_currency"],
                to_currency=tx_data["to_currency"],
                metadata=tx_data["metadata"]
            )
            
            # Process transaction
            start_time = time.time()
            result = await self.framework.optimize_payment(transaction)
            processing_time = time.time() - start_time
            
            # Record results
            processing_times.append(processing_time)
            cost_savings.append(result.cost_savings_percentage)
            
            if result.success:
                success_count += 1
            
            results.append({
                "transaction_id": tx_data["payment_id"],
                "amount": float(tx_data["amount"]),
                "from_currency": tx_data["from_currency"],
                "to_currency": tx_data["to_currency"],
                "success": result.success,
                "cost_savings_percentage": result.cost_savings_percentage,
                "compliance_score": result.compliance_score,
                "processing_time": processing_time,
                "message": result.message
            })
            
            print(f"   ✅ Success: {result.success}")
            print(f"   💰 Cost Savings: {result.cost_savings_percentage:.2f}%")
            print(f"   ⏱️  Processing Time: {processing_time:.3f}s")
            print(f"   📋 Compliance Score: {result.compliance_score:.2f}")
        
        # Calculate metrics
        success_rate = (success_count / len(transactions)) * 100
        avg_processing_time = statistics.mean(processing_times)
        avg_cost_savings = statistics.mean(cost_savings)
        min_cost_savings = min(cost_savings)
        max_cost_savings = max(cost_savings)
        
        benchmark_results = {
            "total_transactions": len(transactions),
            "successful_transactions": success_count,
            "success_rate": success_rate,
            "average_processing_time": avg_processing_time,
            "average_cost_savings": avg_cost_savings,
            "min_cost_savings": min_cost_savings,
            "max_cost_savings": max_cost_savings,
            "processing_times": processing_times,
            "cost_savings": cost_savings,
            "results": results
        }
        
        self.results = results
        return benchmark_results
    
    def validate_performance_targets(self, benchmark_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate performance against targets
        
        Args:
            benchmark_results: Benchmark test results
            
        Returns:
            Dict: Validation results
        """
        print("\n🎯 Validating Performance Targets")
        print("=" * 50)
        
        validation_results = {}
        
        # Validate cost reduction
        avg_cost_savings = benchmark_results["average_cost_savings"]
        cost_reduction_passed = avg_cost_savings >= self.targets["cost_reduction"]
        validation_results["cost_reduction"] = {
            "target": self.targets["cost_reduction"],
            "achieved": avg_cost_savings,
            "passed": cost_reduction_passed,
            "margin": avg_cost_savings - self.targets["cost_reduction"]
        }
        
        print(f"💰 Cost Reduction: {avg_cost_savings:.2f}% (Target: {self.targets['cost_reduction']}%)")
        print(f"   {'✅ PASSED' if cost_reduction_passed else '❌ FAILED'}")
        
        # Validate processing time
        avg_processing_time = benchmark_results["average_processing_time"]
        processing_time_passed = avg_processing_time <= self.targets["processing_time"]
        validation_results["processing_time"] = {
            "target": self.targets["processing_time"],
            "achieved": avg_processing_time,
            "passed": processing_time_passed,
            "margin": self.targets["processing_time"] - avg_processing_time
        }
        
        print(f"⏱️  Processing Time: {avg_processing_time:.3f}s (Target: ≤{self.targets['processing_time']}s)")
        print(f"   {'✅ PASSED' if processing_time_passed else '❌ FAILED'}")
        
        # Validate success rate
        success_rate = benchmark_results["success_rate"]
        success_rate_passed = success_rate >= self.targets["success_rate"]
        validation_results["success_rate"] = {
            "target": self.targets["success_rate"],
            "achieved": success_rate,
            "passed": success_rate_passed,
            "margin": success_rate - self.targets["success_rate"]
        }
        
        print(f"✅ Success Rate: {success_rate:.2f}% (Target: ≥{self.targets['success_rate']}%)")
        print(f"   {'✅ PASSED' if success_rate_passed else '❌ FAILED'}")
        
        # Overall validation
        all_passed = all([
            cost_reduction_passed,
            processing_time_passed,
            success_rate_passed
        ])
        
        validation_results["overall"] = {
            "all_targets_met": all_passed,
            "passed_tests": sum([
                cost_reduction_passed,
                processing_time_passed,
                success_rate_passed
            ]),
            "total_tests": 3
        }
        
        print(f"\n🎯 Overall Validation: {'✅ ALL TARGETS MET' if all_passed else '❌ SOME TARGETS MISSED'}")
        print(f"   Tests Passed: {validation_results['overall']['passed_tests']}/{validation_results['overall']['total_tests']}")
        
        self.validation_results = validation_results
        return validation_results
    
    async def run_stress_test(self, num_transactions: int = 100) -> Dict[str, Any]:
        """
        Run stress test with multiple concurrent transactions
        
        Args:
            num_transactions: Number of concurrent transactions
            
        Returns:
            Dict: Stress test results
        """
        print(f"\n🔥 Running Stress Test ({num_transactions} concurrent transactions)")
        print("=" * 50)
        
        # Create test transactions
        transactions = []
        for i in range(num_transactions):
            transaction = FinancialTransaction(
                transaction_id=f"stress_tx_{i+1:04d}",
                amount=Decimal("100.00"),
                from_currency="USD",
                to_currency="KES",
                metadata={
                    "stress_test": True,
                    "test_id": i+1
                }
            )
            transactions.append(transaction)
        
        # Process transactions concurrently
        start_time = time.time()
        tasks = [self.framework.optimize_payment(tx) for tx in transactions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        success_count = sum(1 for r in successful_results if r.success)
        cost_savings = [r.cost_savings_percentage for r in successful_results if r.success]
        
        stress_results = {
            "total_transactions": num_transactions,
            "successful_transactions": success_count,
            "failed_transactions": len(failed_results),
            "success_rate": (success_count / num_transactions) * 100,
            "total_time": total_time,
            "transactions_per_second": num_transactions / total_time,
            "average_cost_savings": statistics.mean(cost_savings) if cost_savings else 0,
            "min_cost_savings": min(cost_savings) if cost_savings else 0,
            "max_cost_savings": max(cost_savings) if cost_savings else 0
        }
        
        print(f"📊 Stress Test Results:")
        print(f"   Total Transactions: {num_transactions}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {len(failed_results)}")
        print(f"   Success Rate: {stress_results['success_rate']:.2f}%")
        print(f"   Total Time: {total_time:.3f}s")
        print(f"   Transactions/Second: {stress_results['transactions_per_second']:.2f}")
        print(f"   Average Cost Savings: {stress_results['average_cost_savings']:.2f}%")
        
        return stress_results
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive validation report
        
        Returns:
            Dict: Validation report
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capp_reference_version": "1.0.0",
            "sdk_version": "1.0.0",
            "configuration": {
                "region": self.config.region.value,
                "compliance_level": self.config.compliance_level.value,
                "payment_specialization": self.config.payment_specialization,
                "jurisdictions": self.config.jurisdictions
            },
            "performance_targets": self.targets,
            "validation_results": self.validation_results,
            "benchmark_results": self.results,
            "summary": {
                "all_targets_met": self.validation_results.get("overall", {}).get("all_targets_met", False),
                "passed_tests": self.validation_results.get("overall", {}).get("passed_tests", 0),
                "total_tests": self.validation_results.get("overall", {}).get("total_tests", 0)
            }
        }
        
        return report
    
    def save_validation_report(self, report: Dict[str, Any], filename: str = "validation_report.json"):
        """
        Save validation report to file
        
        Args:
            report: Validation report
            filename: Output filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"📄 Validation report saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save validation report: {e}")
    
    def print_validation_summary(self):
        """Print validation summary"""
        print("\n📋 Validation Summary")
        print("=" * 50)
        
        if not self.validation_results:
            print("❌ No validation results available")
            return
        
        overall = self.validation_results.get("overall", {})
        all_passed = overall.get("all_targets_met", False)
        passed_tests = overall.get("passed_tests", 0)
        total_tests = overall.get("total_tests", 0)
        
        print(f"🎯 Overall Result: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
        
        if all_passed:
            print("🎉 CAPP Reference Implementation meets all performance targets!")
            print("✅ Achieves 91% cost reduction")
            print("✅ Meets 1.5s processing time target")
            print("✅ Achieves 95%+ success rate")
        else:
            print("⚠️  Some performance targets were not met")
            print("Please review the detailed results above")


async def run_validation():
    """Run complete validation suite"""
    try:
        # Load configuration
        config = load_capp_config()
        
        # Validate configuration
        if not validate_config(config):
            print("❌ Configuration validation failed")
            return
        
        # Print configuration summary
        from .config import print_config_summary
        print_config_summary(config)
        
        # Initialize validator
        validator = PerformanceValidator(config)
        await validator.initialize()
        
        # Run benchmark tests
        benchmark_results = await validator.run_benchmark_tests()
        
        # Validate performance targets
        validation_results = validator.validate_performance_targets(benchmark_results)
        
        # Run stress test
        stress_results = await validator.run_stress_test(50)
        
        # Generate and save report
        report = validator.generate_validation_report()
        report["stress_test_results"] = stress_results
        
        validator.save_validation_report(report)
        
        # Print summary
        validator.print_validation_summary()
        
        return report
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_validation()) 