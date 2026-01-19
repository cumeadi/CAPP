from fastapi import APIRouter, HTTPException, Depends, Request
from .. import schemas
from applications.capp.capp.core.router import PaymentRouter, RouteOption
import structlog
from applications.capp.capp.core.limiter import limiter

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/routing",
    tags=["routing"]
)

@router.post("/calculate", response_model=schemas.RoutingResponse)
@limiter.limit("5/minute")
async def calculate_route(routing_req: schemas.RoutingRequest, request: Request):
    """
    Calculate optimal payment routes based on amount, recipient, and preference.
    """
    try:
        logger.info("routing_calculation_started", 
                    amount=float(routing_req.amount), 
                    currency=routing_req.currency)
        
        # Resilience: Circuit Breaker
        from applications.capp.capp.services.circuit_breaker import get_circuit_breaker
        cb = get_circuit_breaker("routing_engine")
        
        if cb.is_open():
             raise HTTPException(status_code=503, detail="Routing Engine Circuit OPEN (Downstream Failure)")

        try:
            # Use new Adapter Logic
            logger.info("loading_routing_service")
            from applications.capp.capp.services.routing_service import RoutingService
            from applications.capp.capp.models.payments import PaymentPreferences
            
            engine = RoutingService()
            
            logger.info("mapping_preferences", req_pref=routing_req.preference)
            # Map request to preferences
            prefs = PaymentPreferences(
                prioritize_cost=(routing_req.preference in ["CHEAP", "CHEAPEST"]),
                prioritize_speed=(routing_req.preference in ["FAST", "FASTEST"])
            )
            
            logger.info("calculating_routes")
            # Calculate Routes (returns List[dict])
            quotes = await engine.calculate_best_route(
                amount=routing_req.amount, 
                currency="USDC", # MVP assumption
                destination=routing_req.recipient, 
                preferences=prefs
            )
            logger.info("routes_calculated", count=len(quotes))
            
            # Record Success if we get here
            cb.record_success()
            
        except Exception as e:
            # Record Failure
            cb.record_failure()
            logger.error("Routing calculation internal error", error=str(e), traceback=True)
            raise e
        
        # Map DTOs to Schema
        api_routes = []
        best_route = None
        
        for q in quotes:
            try:
                route_model = schemas.PaymentRoute(
                    chain=q["rail"],
                    fee_usd=q["fee"],
                    eta_seconds=int(q["estimated_time_minutes"] * 60),
                    recommendation_score=q["score"],
                    reason=f"Fee: {q['fee']}, Time: {q['estimated_time_minutes']}m",
                    estimated_gas_token=0.0 # Mock
                )
                api_routes.append(route_model)
            except Exception as map_err:
                 logger.error("mapping_error", quote=q, error=str(map_err))
        
        if api_routes:
            best_route = api_routes[0] # Already sorted by service

        return {
            "routes": api_routes,
            "recommended_route": best_route
        }
    except Exception as e:
        logger.error("Routing calculation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
