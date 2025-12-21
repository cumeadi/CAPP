import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Optional, Dict, Any, List
import structlog

from applications.capp.capp.models.payments import CrossBorderPayment, PaymentRoute

logger = structlog.get_logger(__name__)

class PaymentRoutingEnv(gym.Env):
    """
    Custom Environment that follows gym interface.
    The agent learns to select the best route from a list of candidates.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, max_candidate_routes: int = 5):
        super(PaymentRoutingEnv, self).__init__()
        
        self.max_candidate_routes = max_candidate_routes
        
        # Define action space: Select one of N routes
        self.action_space = spaces.Discrete(max_candidate_routes)
        
        # Define observation space
        # We need to represent:
        # 1. Transaction details (Amount, Country Pair)
        # 2. Features for each of the N candidate routes (Cost, Speed, Reliability)
        
        # Simplified Feature Vector per Route: [Fees (%), Time (norm), Reliability (0-1), Compliance (0-1), IsValid (0/1)]
        # Total Dimension = (N * 5) + Context Features (Amount norm)
        self.features_per_route = 5
        self.context_features = 1
        
        total_obs_dim = (self.max_candidate_routes * self.features_per_route) + self.context_features
        
        self.observation_space = spaces.Box(
            low=0, 
            high=1, 
            shape=(total_obs_dim,), 
            dtype=np.float32
        )
        
        self.current_routes: List[Dict[str, float]] = []
        self.current_payment: Optional[Dict[str, Any]] = None

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None):
        """
        Reset the state of the environment to an initial state.
        For RL training, this usually involves generating a random transaction and random potential routes.
        """
        super().reset(seed=seed)
        
        # Generate synthetic data if not provided in options
        if options and 'payment' in options and 'routes' in options:
            self.current_payment = options['payment']
            self.current_routes = options['routes']
        else:
            self._generate_synthetic_episode()
            
        return self._get_observation(), {}

    def step(self, action):
        """
        Execute one time step within the environment
        """
        selected_route_idx = int(action)
        
        # Check if selected route is valid
        if selected_route_idx >= len(self.current_routes):
            # Agent selected a non-existent route (if we have fewer than Max routes)
            # This should be heavily penalized
            reward = -10.0
            terminated = True
            truncated = False
            info = {"is_success": False, "reason": "invalid_selection"}
            return self._get_observation(), reward, terminated, truncated, info

        route = self.current_routes[selected_route_idx]
        
        # Calculate Reward
        # R = Success + (w_cost * -cost) + (w_time * -time) + Reliability
        
        # Synthetic outcome based on reliability
        is_success = np.random.random() < route['reliability']
        
        if not is_success:
            reward = -5.0
            info = {"is_success": False, "reason": "failed_execution"}
        else:
            # Normalize components
            # Cost: 0.01 (1%) is bad, 0.0 is good. Map to negative reward.
            cost_penalty = float(route['fees']) * 100 # e.g., 0.01 -> -1.0
            
            # Time: 0 (instant) is good, 1.0 (max time) is bad.
            time_penalty = float(route['time']) * 2 # e.g., 0.5 -> -1.0
            
            reward = 10.0 - cost_penalty - time_penalty
            info = {"is_success": True}

        terminated = True # One-step environment
        truncated = False
        
        return self._get_observation(), reward, terminated, truncated, info

    def _get_observation(self):
        """
        Construct the observation vector from current state
        """
        obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        
        # 1. Context Features
        if self.current_payment:
            # Normalize amount (log scale or simple capping)
            obs[0] = min(float(self.current_payment.get('amount', 0)) / 10000.0, 1.0)
        
        # 2. Route Features
        for i, route in enumerate(self.current_routes):
            if i >= self.max_candidate_routes:
                break
                
            start_idx = self.context_features + (i * self.features_per_route)
            
            obs[start_idx] = route.get('fees', 0.0)
            obs[start_idx+1] = route.get('time', 1.0) # Normalized time
            obs[start_idx+2] = route.get('reliability', 0.0)
            obs[start_idx+3] = route.get('compliance', 0.0)
            obs[start_idx+4] = 1.0 # IsValid flag
            
        return obs

    def _generate_synthetic_episode(self):
        """Generate random payment and routes for training"""
        self.current_payment = {
            'amount': np.random.uniform(100, 5000)
        }
        
        num_routes = np.random.randint(1, self.max_candidate_routes + 1)
        self.current_routes = []
        
        for _ in range(num_routes):
            # Inverse correlation between cost and speed usually
            fees = np.random.uniform(0.001, 0.05)
            time = np.random.uniform(0, 1.0)
            reliability = np.random.uniform(0.8, 1.0)
            
            # Better routes are rare
            if np.random.random() < 0.1:
                fees = 0.005
                time = 0.1
                reliability = 0.99
                
            self.current_routes.append({
                'fees': fees,
                'time': time,
                'reliability': reliability,
                'compliance': 1.0
            })
            
    def render(self, mode='human'):
        pass
    
    def close(self):
        pass
