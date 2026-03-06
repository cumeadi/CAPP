import os
from . import schemas

# Global Config Store (In-Memory for MVP)
# AUTONOMY_LEVEL controls transaction gating:
#   COPILOT   – every send requires human approval (safest; use in production)
#   GUARDED   – sends > $1 000 require approval (default for dev/testnet)
#   SOVEREIGN – fully autonomous, no approval gate (use only in controlled tests)
app_config = schemas.AgentConfig(
    autonomy_level=os.environ.get("AUTONOMY_LEVEL", "GUARDED")
)
