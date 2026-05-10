import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Mock settings for testing
from app.config import settings

async def test_gemini_configured():
    from app.services.gemini_service import is_gemini_configured
    print(f"Gemini Configured: {is_gemini_configured()}")
    if settings.GEMINI_API_KEY:
        print(f"Gemini Key ends with: ...{settings.GEMINI_API_KEY[-4:]}")

async def test_gemini_stream():
    from app.services.gemini_service import _gemini_stream
    
    print("\nTesting Gemini Stream...")
    try:
        async for chunk in _gemini_stream("You are a helpful assistant", "Say exactly 'Hello World'"):
            print(chunk, end="", flush=True)
    except Exception as e:
        print(f"\nError during streaming: {e}")

async def test_status_endpoint():
    from app.routers.generate import generation_status
    print("\n\nTesting Status Endpoint...")
    status = await generation_status()
    print(f"Status: {status}")

if __name__ == "__main__":
    asyncio.run(test_gemini_configured())
    asyncio.run(test_gemini_stream())
    asyncio.run(test_status_endpoint())
