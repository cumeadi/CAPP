from typing import Dict, Optional, Tuple
from datetime import datetime
import asyncio
import structlog

logger = structlog.get_logger(__name__)

class CircuitBreaker:
    """
    Circuit Breaker pattern to fail fast when external service is down.
    States: CLOSED (Normal), OPEN (Failing/Paused), HALF-OPEN (Testing)
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold # Max failures before opening
        self.recovery_timeout = recovery_timeout   # Seconds to wait before retrying (Half-Open)
        
        self.failures = 0
        self.state = "CLOSED" 
        self.last_failure_time = None

    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        self.failures += 1
        self.last_failure_time = datetime.now()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit Breaker OPENED", failures=self.failures)

    def record_success(self):
        """Record success and reset circuit if needed"""
        if self.state != "CLOSED":
            logger.info("Circuit Breaker Recovered (CLOSED)")
        
        self.failures = 0
        self.state = "CLOSED"

    def is_open(self) -> bool:
        """Check if circuit is open (requests should be blocked)"""
        if self.state == "CLOSED":
            return False
            
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed > self.recovery_timeout:
                self.state = "HALF-OPEN" # Allow one trial
                logger.info("Circuit Breaker HALF-OPEN (Trial)")
                return False # Allow this request to try
            return True # Still Open
            
        return False # Half-Open allows trial


# Global Registry
_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(service_name: str, threshold: int = 5, timeout: int = 60) -> CircuitBreaker:
    if service_name not in _breakers:
        _breakers[service_name] = CircuitBreaker(threshold, timeout)
    return _breakers[service_name]
