"""
CAPP Reference Implementation Utilities

Utility functions for transaction creation, response formatting,
and other helper functions used by the CAPP reference implementation.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal

from canza_agents import FinancialTransaction


def create_transaction_from_request(request) -> FinancialTransaction:
    """
    Create FinancialTransaction from payment request
    
    Args:
        request: Payment request object
        
    Returns:
        FinancialTransaction: Created transaction
    """
    # Build metadata
    metadata = {
        "sender_info": request.sender_info,
        "recipient_info": request.recipient_info,
        "urgency": request.urgency,
        "payment_purpose": request.payment_purpose
    }
    
    # Add additional metadata if provided
    if request.metadata:
        metadata.update(request.metadata)
    
    # Create transaction
    transaction = FinancialTransaction(
        transaction_id=request.payment_id,
        amount=request.amount,
        from_currency=request.from_currency,
        to_currency=request.to_currency,
        metadata=metadata
    )
    
    return transaction


def format_response(request, result, processing_time: float) -> Dict[str, Any]:
    """
    Format response to match original CAPP API
    
    Args:
        request: Original payment request
        result: Framework result
        processing_time: Processing time in seconds
        
    Returns:
        Dict: Formatted response
    """
    # Extract agent recommendations
    agent_recommendations = {}
    if hasattr(result, 'agent_results') and result.agent_results:
        for agent_result in result.agent_results:
            agent_recommendations[agent_result.agent_type] = {
                "confidence": agent_result.confidence,
                "recommendation": agent_result.recommendation,
                "processing_time": agent_result.processing_time
            }
    
    # Build optimal route information
    optimal_route = {
        "route_type": getattr(result, 'optimal_route_type', 'direct'),
        "providers": getattr(result, 'optimal_providers', []),
        "cost": getattr(result, 'optimal_cost', 0.0),
        "processing_time": getattr(result, 'optimal_processing_time', 0.0),
        "reliability_score": getattr(result, 'optimal_reliability_score', 0.0)
    }
    
    # Build response
    response = {
        "payment_id": request.payment_id,
        "success": getattr(result, 'success', False),
        "cost_savings_percentage": getattr(result, 'cost_savings_percentage', 0.0),
        "compliance_score": getattr(result, 'compliance_score', 0.0),
        "risk_score": getattr(result, 'risk_score', 0.0),
        "processing_time": processing_time,
        "optimal_route": optimal_route,
        "agent_recommendations": agent_recommendations,
        "message": getattr(result, 'message', 'Payment processed successfully'),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return response


def validate_payment_request(request) -> bool:
    """
    Validate payment request
    
    Args:
        request: Payment request to validate
        
    Returns:
        bool: True if request is valid
    """
    try:
        # Check required fields
        if not request.payment_id:
            return False
        
        if not request.amount or request.amount <= 0:
            return False
        
        if not request.from_currency or not request.to_currency:
            return False
        
        if not request.sender_info or not request.recipient_info:
            return False
        
        # Validate sender info
        if not request.sender_info.get("id"):
            return False
        
        if not request.sender_info.get("country"):
            return False
        
        # Validate recipient info
        if not request.recipient_info.get("id"):
            return False
        
        if not request.recipient_info.get("country"):
            return False
        
        # Validate urgency
        valid_urgency_levels = ["low", "standard", "high", "urgent"]
        if request.urgency not in valid_urgency_levels:
            return False
        
        # Validate payment purpose
        valid_purposes = ["general", "business", "personal", "investment", "charity"]
        if request.payment_purpose not in valid_purposes:
            return False
        
        return True
        
    except Exception:
        return False


def calculate_performance_metrics(results: list) -> Dict[str, Any]:
    """
    Calculate performance metrics from results
    
    Args:
        results: List of payment results
        
    Returns:
        Dict: Performance metrics
    """
    if not results:
        return {
            "total_transactions": 0,
            "successful_transactions": 0,
            "success_rate": 0.0,
            "average_cost_savings": 0.0,
            "average_processing_time": 0.0,
            "average_compliance_score": 0.0,
            "average_risk_score": 0.0
        }
    
    total_transactions = len(results)
    successful_transactions = sum(1 for r in results if r.get("success", False))
    success_rate = (successful_transactions / total_transactions) * 100
    
    cost_savings = [r.get("cost_savings_percentage", 0.0) for r in results]
    processing_times = [r.get("processing_time", 0.0) for r in results]
    compliance_scores = [r.get("compliance_score", 0.0) for r in results]
    risk_scores = [r.get("risk_score", 0.0) for r in results]
    
    metrics = {
        "total_transactions": total_transactions,
        "successful_transactions": successful_transactions,
        "success_rate": success_rate,
        "average_cost_savings": sum(cost_savings) / len(cost_savings),
        "average_processing_time": sum(processing_times) / len(processing_times),
        "average_compliance_score": sum(compliance_scores) / len(compliance_scores),
        "average_risk_score": sum(risk_scores) / len(risk_scores),
        "min_cost_savings": min(cost_savings),
        "max_cost_savings": max(cost_savings),
        "min_processing_time": min(processing_times),
        "max_processing_time": max(processing_times)
    }
    
    return metrics


def format_error_response(error: str, payment_id: str = None) -> Dict[str, Any]:
    """
    Format error response
    
    Args:
        error: Error message
        payment_id: Payment ID if available
        
    Returns:
        Dict: Formatted error response
    """
    response = {
        "success": False,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if payment_id:
        response["payment_id"] = payment_id
    
    return response


def log_payment_request(request, processing_time: float, result):
    """
    Log payment request for monitoring
    
    Args:
        request: Payment request
        processing_time: Processing time
        result: Processing result
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payment_id": request.payment_id,
        "amount": float(request.amount),
        "from_currency": request.from_currency,
        "to_currency": request.to_currency,
        "sender_country": request.sender_info.get("country"),
        "recipient_country": request.recipient_info.get("country"),
        "urgency": request.urgency,
        "processing_time": processing_time,
        "success": getattr(result, 'success', False),
        "cost_savings_percentage": getattr(result, 'cost_savings_percentage', 0.0),
        "compliance_score": getattr(result, 'compliance_score', 0.0),
        "risk_score": getattr(result, 'risk_score', 0.0)
    }
    
    # In a real implementation, this would be logged to a proper logging system
    print(f"📊 Payment Log: {log_entry}")


def create_test_transaction() -> Dict[str, Any]:
    """
    Create a test transaction for validation
    
    Returns:
        Dict: Test transaction data
    """
    return {
        "payment_id": "test_tx_001",
        "amount": Decimal("1000.00"),
        "from_currency": "USD",
        "to_currency": "KES",
        "sender_info": {
            "id": "sender_001",
            "country": "US",
            "name": "John Doe",
            "email": "john.doe@example.com"
        },
        "recipient_info": {
            "id": "recipient_001",
            "country": "KE",
            "name": "Jane Smith",
            "phone": "+254700000000",
            "email": "jane.smith@example.com"
        },
        "urgency": "standard",
        "payment_purpose": "general",
        "metadata": {
            "test_transaction": True,
            "reference": "TEST_001"
        }
    }


def create_benchmark_transactions() -> list:
    """
    Create benchmark transactions for performance testing
    
    Returns:
        List: Benchmark transaction data
    """
    transactions = []
    
    # Different transaction types for benchmarking
    transaction_types = [
        {
            "amount": Decimal("100.00"),
            "from_currency": "USD",
            "to_currency": "KES",
            "urgency": "low"
        },
        {
            "amount": Decimal("500.00"),
            "from_currency": "EUR",
            "to_currency": "NGN",
            "urgency": "standard"
        },
        {
            "amount": Decimal("1000.00"),
            "from_currency": "GBP",
            "to_currency": "UGX",
            "urgency": "high"
        },
        {
            "amount": Decimal("2500.00"),
            "from_currency": "USD",
            "to_currency": "GHS",
            "urgency": "urgent"
        },
        {
            "amount": Decimal("5000.00"),
            "from_currency": "EUR",
            "to_currency": "TZS",
            "urgency": "standard"
        }
    ]
    
    for i, tx_type in enumerate(transaction_types):
        transaction = {
            "payment_id": f"benchmark_tx_{i+1:03d}",
            "amount": tx_type["amount"],
            "from_currency": tx_type["from_currency"],
            "to_currency": tx_type["to_currency"],
            "sender_info": {
                "id": f"sender_{i+1:03d}",
                "country": "US",
                "name": f"Sender {i+1}",
                "email": f"sender{i+1}@example.com"
            },
            "recipient_info": {
                "id": f"recipient_{i+1:03d}",
                "country": "KE",
                "name": f"Recipient {i+1}",
                "phone": f"+254700000{i+1:03d}",
                "email": f"recipient{i+1}@example.com"
            },
            "urgency": tx_type["urgency"],
            "payment_purpose": "general",
            "metadata": {
                "benchmark_transaction": True,
                "benchmark_id": i+1
            }
        }
        transactions.append(transaction)
    
    return transactions


def format_analytics_response(analytics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format analytics response
    
    Args:
        analytics: Raw analytics data
        
    Returns:
        Dict: Formatted analytics response
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "framework": analytics.get("framework", {}),
        "providers": analytics.get("providers", {}),
        "liquidity_pools": analytics.get("liquidity_pools", 0),
        "capp_reference": analytics.get("capp_reference", {}),
        "summary": {
            "total_transactions": analytics.get("capp_reference", {}).get("total_transactions", 0),
            "total_cost_savings": analytics.get("capp_reference", {}).get("total_cost_savings", 0.0),
            "average_processing_time": analytics.get("capp_reference", {}).get("average_processing_time", 0.0),
            "uptime": analytics.get("capp_reference", {}).get("uptime", "100%"),
            "version": analytics.get("capp_reference", {}).get("version", "1.0.0")
        }
    } 