from typing import Dict, Optional, Callable, Awaitable, TypeVar
from datetime import datetime
import asyncio
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitBreaker:
    """
    Circuit Breaker pattern to fail fast when external service is down.
    States: CLOSED (normal), OPEN (failing/paused), HALF-OPEN (testing recovery).
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold  # failures before opening
        self.recovery_timeout = recovery_timeout    # seconds before half-open trial

        self.failures = 0
        self.state = "CLOSED"
        self.last_failure_time: Optional[datetime] = None

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("circuit_breaker_opened", failures=self.failures)

    def record_success(self):
        if self.state != "CLOSED":
            logger.info("circuit_breaker_recovered")
        self.failures = 0
        self.state = "CLOSED"

    def is_open(self) -> bool:
        if self.state == "CLOSED":
            return False
        if self.state == "OPEN":
            elapsed = (datetime.now() - self.last_failure_time).total_seconds()
            if elapsed > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info("circuit_breaker_half_open")
                return False  # allow trial request
            return True
        return False  # HALF-OPEN allows the trial

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """
        Execute an async callable under this circuit breaker.

        Raises RuntimeError immediately if the circuit is open.
        Records success/failure automatically.

        Usage:
            result = await breaker.call(lambda: some_async_func(args))
        """
        if self.is_open():
            raise RuntimeError(f"Circuit breaker is OPEN — service unavailable")
        try:
            result = await fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


# Global registry — one breaker per named service
_breakers: Dict[str, "CircuitBreaker"] = {}


def get_circuit_breaker(
    service_name: str, threshold: int = 5, timeout: int = 60
) -> "CircuitBreaker":
    if service_name not in _breakers:
        _breakers[service_name] = CircuitBreaker(threshold, timeout)
    return _breakers[service_name]
