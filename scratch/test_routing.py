import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Mock settings for testing
from app.config import settings

async def test_deepseek_configured():
    from app.services.deepseek_service import is_deepseek_configured
    print(f"DeepSeek Configured: {is_deepseek_configured()}")
    if settings.DEEPSEEK_API_KEY:
        print(f"DeepSeek Key ends with: ...{settings.DEEPSEEK_API_KEY[-4:]}")

async def test_claude_fallback():
    from app.services.claude_service import _claude_stream
    
    # Temporarily break Claude to force fallback
    original_key = settings.ANTHROPIC_API_KEY
    settings.ANTHROPIC_API_KEY = "your-invalid-key"
    
    print("\nTesting Claude Fallback (should use DeepSeek)...")
    try:
        async for chunk in _claude_stream("You are a helper", "Say hello"):
            print(chunk, end="", flush=True)
    except Exception as e:
        print(f"Error during fallback: {e}")
    finally:
        settings.ANTHROPIC_API_KEY = original_key

async def test_status_endpoint():
    from app.routers.generate import generation_status
    print("\n\nTesting Status Endpoint...")
    status = await generation_status()
    print(f"Status: {status}")

if __name__ == "__main__":
    asyncio.run(test_deepseek_configured())
    asyncio.run(test_status_endpoint())
    # asyncio.run(test_claude_fallback()) # Uncomment to test actual API call if key is valid
