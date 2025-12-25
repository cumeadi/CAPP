
import asyncio
import sys
import os
import structlog

# Setup paths (similar to what's in agents.py/analyst.py)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

try:
    from packages.intelligence.market.analyst import MarketAnalysisAgent
except ImportError:
    # If the path hack above isn't enough, try adding CAPP/CAPP
    sys.path.append("/Users/chikau/CAPP/CAPP")
    from packages.intelligence.market.analyst import MarketAnalysisAgent

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def reproduce_failure():
    print("Initializing Agent...")
    try:
        agent = MarketAnalysisAgent()
        print("Agent Initialized.")
        
        query = "yield scan"
        print(f"Sending Query: {query}")
        
        response = await agent.chat_with_analyst(query)
        print("Response received:")
        print(response)
        
    except Exception as e:
        print("\n!!! CAUGHT EXCEPTION !!!")
        print(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(reproduce_failure())
