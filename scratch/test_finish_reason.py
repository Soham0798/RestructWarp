import asyncio
import os
import sys

sys.path.append(os.getcwd())
from app.services.gemini_service import _gemini_stream

async def test_truncation():
    print("Testing long generation...")
    # Ask it to generate a very long list to test if it hits limits
    prompt = "Generate a list of numbers from 1 to 10000, one per line."
    system = "You are a helpful assistant."
    
    count = 0
    async for chunk in _gemini_stream(system, prompt):
        count += len(chunk)
        if count > 5000:
            break
            
    print(f"\nStreamed {count} bytes successfully.")

if __name__ == "__main__":
    asyncio.run(test_truncation())
