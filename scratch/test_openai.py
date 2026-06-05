import asyncio
import os
import sys

# Add root directory to sys.path
sys.path.append(os.getcwd())

from app.config import settings

async def test_openai_stream():
    from app.services.groq_service import stream_website_openai
    print("Testing OpenAI stream fallback...")
    
    # Verify OpenAI API Key is loaded
    if not settings.OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY is not set in settings!")
        return
        
    print(f"Loaded OPENAI_API_KEY: {settings.OPENAI_API_KEY[:10]}...")
    
    # Try calling stream_website_openai
    try:
        async for chunk in stream_website_openai("A simple button that turns green when clicked"):
            print(chunk, end="", flush=True)
        print("\nSuccess!")
    except Exception as e:
        print(f"\nFailed with error: {e}")

async def test_status():
    from app.routers.generate import generation_status
    print("\nTesting status endpoint with Gemini disabled...")
    
    original_gemini = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = "" # Disable gemini to check fallback engine status
    
    try:
        status = await generation_status()
        print(f"Status response: {status}")
    finally:
        settings.GEMINI_API_KEY = original_gemini

if __name__ == "__main__":
    asyncio.run(test_openai_stream())
    asyncio.run(test_status())
