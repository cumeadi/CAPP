import os
import structlog
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

from packages.ml.environments.payment_routing_env import PaymentRoutingEnv

logger = structlog.get_logger(__name__)

def train_agent(total_timesteps: int = 10000, save_path: str = "packages/ml/models/route_optimization_model"):
    """
    Train the PPO agent on the PaymentRoutingEnv
    """
    logger.info("Starting training...")
    
    # Create environment
    env = PaymentRoutingEnv()
    
    # Check custom environment
    check_env(env)
    logger.info("Environment check passed")
    
    # Initialize PPO agent
    model = PPO("MlpPolicy", env, verbose=1)
    
    # Train
    model.learn(total_timesteps=total_timesteps)
    logger.info("Training completed")
    
    # Save model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save(save_path)
    logger.info(f"Model saved to {save_path}")

if __name__ == "__main__":
    train_agent()
