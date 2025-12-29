from fastapi import APIRouter, HTTPException, Depends
from .. import schemas
from applications.capp.capp.core.router import PaymentRouter, RouteOption
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/routing",
    tags=["routing"]
)

@router.post("/calculate", response_model=schemas.RoutingResponse)
async def calculate_route(request: schemas.RoutingRequest):
    """
    Calculate optimal payment routes based on amount, recipient, and preference.
    """
    try:
        engine = PaymentRouter()
        
        # Calculate Mocked Routes
        routes_dtos = await engine.calculate_routes(
            amount_usd=request.amount, 
            recipient=request.recipient, 
            preference=request.preference
        )
        
        # Map DTOs to Schema
        api_routes = []
        best_score = -1000
        best_route = None
        
        for r in routes_dtos:
            route_model = schemas.PaymentRoute(
                chain=r.chain,
                fee_usd=r.fee_usd,
                eta_seconds=r.eta_seconds,
                recommendation_score=r.recommendation_score,
                reason=r.reason,
                estimated_gas_token=r.estimated_gas_token
            )
            api_routes.append(route_model)
            
            if route_model.recommendation_score > best_score:
                best_score = route_model.recommendation_score
                best_route = route_model
        
        if not best_route and api_routes:
            best_route = api_routes[0]

        return {
            "routes": api_routes,
            "recommended_route": best_route
        }
    except Exception as e:
        logger.error("Routing calculation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
