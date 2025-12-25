
import asyncio
import os
import sys
import structlog

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# Add CAPP root to path if needed (duplicate logic to be safe)
sys.path.append("/Users/chikau/CAPP/CAPP")

from packages.intelligence.core.gemini_provider import GeminiProvider

# Configure logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
)
logger = structlog.get_logger()

async def verify_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment")
        return

    print(f"Initializing GeminiProvider with key ending in ...{api_key[-4:]}")
    
    try:
        provider = GeminiProvider(api_key=api_key, model_name="gemini-2.0-flash")
        
        # Test 1: Simple Text Generation
        print("\n--- Test 1: Text Generation ---")
        prompt = "Explain 'Universal Liquidity' in one sentence."
        print(f"Prompt: {prompt}")
        
        response = await provider.generate_text(prompt)
        print(f"Response: {response.content}")
        
        if not response.content:
            print("❌ Failed to get text content")
            return

        # Test 2: JSON Generation
        print("\n--- Test 2: JSON Generation ---")
        prompt = "Analyze the sentiment of this phrase: 'The market is crashing but I am buying.'"
        schema = {"sentiment": "string", "confidence": "float"}
        print(f"Prompt: {prompt}")
        
        json_response = await provider.generate_json(prompt, schema)
        print(f"JSON Response: {json_response}")
        
        if "sentiment" in json_response:
             print("✅ Verification Successful!")
        else:
             print("❌ JSON structure mismatch")

    except Exception as e:
        print(f"\n❌ Exception during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(verify_gemini())
