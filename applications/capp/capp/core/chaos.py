
import os
import random
import time
import functools
import structlog
from typing import Optional, Any, Callable, Type
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

class ChaosConfig(BaseModel):
    enabled: bool = False
    failure_rate: float = 0.5  # 50% chance of failure when enabled
    latency_ms: int = 0        # Added latency in ms
    exception_type: str = "RuntimeError"
    exception_msg: str = "🔥 Chaos Monkey Strike!"

class ChaosMonkey:
    _instance: Optional['ChaosMonkey'] = None
    
    def __init__(self):
        self.config = self._load_config()
        if self.config.enabled:
            logger.warning("🐒 CHAOS MONKEY IS ENABLED! EXPECT FAILURES.", config=self.config.dict())

    @classmethod
    def get_instance(cls) -> 'ChaosMonkey':
        if cls._instance is None:
            cls._instance = ChaosMonkey()
        return cls._instance

    def _load_config(self) -> ChaosConfig:
        return ChaosConfig(
            enabled=os.getenv("CHAOS_ENABLED", "false").lower() == "true",
            failure_rate=float(os.getenv("CHAOS_FAILURE_RATE", "0.5")),
            latency_ms=int(os.getenv("CHAOS_LATENCY_MS", "0")),
            exception_type=os.getenv("CHAOS_EXCEPTION_TYPE", "RuntimeError"),
            exception_msg=os.getenv("CHAOS_EXCEPTION_MSG", "🔥 Chaos Monkey Strike!")
        )

    def should_fail(self) -> bool:
        if not self.config.enabled:
            return False
        return random.random() < self.config.failure_rate

    def inject_latency(self):
        if self.config.enabled and self.config.latency_ms > 0:
            time.sleep(self.config.latency_ms / 1000.0)

    def raise_chaos(self):
        if self.config.exception_type == "TimeoutError":
            raise TimeoutError(self.config.exception_msg)
        elif self.config.exception_type == "ValueError":
            raise ValueError(self.config.exception_msg)
        else:
            raise RuntimeError(self.config.exception_msg)

def chaos_inject(func: Callable) -> Callable:
    """Decorator to inject chaos into a function."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        monkey = ChaosMonkey.get_instance()
        
        # 1. Latency injection (always happens if enabled)
        monkey.inject_latency()

        # 2. Failure injection (probabilistic)
        if monkey.should_fail():
            logger.warning(f"🐒 Chaos Monkey striking function: {func.__name__}")
            monkey.raise_chaos()

        return await func(*args, **kwargs)
    return wrapper

# Sync version if needed
def chaos_inject_sync(func: Callable) -> Callable:
    """Decorator to inject chaos into a sync function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        monkey = ChaosMonkey.get_instance()
        monkey.inject_latency()
        if monkey.should_fail():
            logger.warning(f"🐒 Chaos Monkey striking function: {func.__name__}")
            monkey.raise_chaos()
        return func(*args, **kwargs)
    return wrapper
