import os

# API Keys (For MVP, we set default here if not found in env - DO NOT COMMIT REAL KEYS IN PROD)
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "FX7-uiaeRx_TaEyI2HGC0")

# RPC URLs
POLYGON_RPC_URL = f"https://polygon-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"

# Chain IDs
CHAIN_ID_POLYGON = 137

# Feature Flags
ENABLE_MULTI_CHAIN = True
