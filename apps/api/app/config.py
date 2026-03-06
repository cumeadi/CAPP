import os

# API Keys - MUST be set via environment variable. No default is provided intentionally.
# If this value is missing the application will fail loudly at startup.
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
if not ALCHEMY_API_KEY:
    raise RuntimeError(
        "ALCHEMY_API_KEY environment variable is not set. "
        "Set it in your .env file or deployment secrets manager. "
        "Never hard-code API keys in source code."
    )

# RPC URLs
POLYGON_RPC_URL = f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Chain IDs
CHAIN_ID_POLYGON = 137

# Feature Flags
ENABLE_MULTI_CHAIN = True
