from fastapi import APIRouter
from typing import Dict, Any

from applications.capp.capp.agents.liquidity.liquidity_agent import LiquidityAgent, LiquidityConfig

router = APIRouter()

@router.get("/status")
async def check_corridor_liquidity():
    """
    Check current liquidity status across all corridors
    """
    # Initialize the liquidity agent with default configuration
    # This fetches the current mock/cache pools available
    config = LiquidityConfig()
    agent = LiquidityAgent(config)
    
    pools = await agent.get_all_pools_status()
    
    return {
        "status": "success",
        "corridors": [
            {
                "pool_id": pool.pool_id,
                "currency_pair": pool.currency_pair,
                "available_liquidity": float(pool.available_liquidity),
                "total_liquidity": float(pool.total_liquidity),
                "utilization_rate": pool.utilization_rate,
                "pool_status": pool.status
            }
            for pool in pools.values()
        ]
    }
