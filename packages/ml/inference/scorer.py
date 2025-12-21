import numpy as np
import structlog
from typing import List, Optional, Dict, Any
from stable_baselines3 import PPO

from applications.capp.capp.models.payments import CrossBorderPayment, PaymentRoute
from packages.ml.config import MLConfig

logger = structlog.get_logger(__name__)

class RLRouteScorer:
    """
    Scorer that uses a trained RL model to select the optimal route.
    """
    
    def __init__(self, model_path: str = MLConfig.MODEL_PATH):
        self.model = None
        self.model_path = model_path
        self._load_model()
        
    def _load_model(self):
        try:
            self.model = PPO.load(self.model_path)
            logger.info(f"Loaded RL model from {self.model_path}")
        except Exception as e:
            logger.warning(f"Could not load RL model from {self.model_path}. Using fallback.", error=str(e))
            self.model = None

    def select_best_route_index(self, payment: CrossBorderPayment, routes: List[PaymentRoute]) -> int:
        """
        Predict the best route index using the RL model.
        """
        if not self.model or not routes:
            return 0 # Fallback to first route
            
        # Construct Observation
        obs = self._construct_observation(payment, routes)
        
        # Predict
        action, _states = self.model.predict(obs, deterministic=True)
        
        selected_idx = int(action)
        
        # Safety check
        if selected_idx >= len(routes):
            logger.warning("Agent selected invalid route index", index=selected_idx, num_routes=len(routes))
            return 0
            
        return selected_idx

    def _construct_observation(self, payment: CrossBorderPayment, routes: List[PaymentRoute]) -> np.ndarray:
        """
        Construct observation vector from payment and routes.
        Must match PaymentRoutingEnv._get_observation logic.
        """
        # Dimensions from env
        max_candidate_routes = MLConfig.MAX_CANDIDATE_ROUTES
        features_per_route = 5
        context_features = 1
        total_obs_dim = (max_candidate_routes * features_per_route) + context_features
        
        obs = np.zeros(total_obs_dim, dtype=np.float32)
        
        # 1. Context Features
        obs[0] = min(float(payment.amount) / 10000.0, 1.0)
        
        # 2. Route Features
        for i, route in enumerate(routes):
            if i >= max_candidate_routes:
                break
                
            start_idx = context_features + (i * features_per_route)
            
            # Extract features
            # Fees: Normalize assuming 0-5% range
            fees_pct = float(route.fees) / max(float(payment.amount), 1.0)
            
            # Time: Normalize assuming 0-1440 mins
            time_norm = min(float(route.estimated_delivery_time) / 1440.0, 1.0)
            
            obs[start_idx] = fees_pct
            obs[start_idx+1] = time_norm
            obs[start_idx+2] = route.reliability_score
            # We don't have compliance score in the route object directly, using placeholder or default
            obs[start_idx+3] = 1.0 
            obs[start_idx+4] = 1.0 # IsValid
            
        return obs
