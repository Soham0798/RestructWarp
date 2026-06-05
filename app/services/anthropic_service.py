"""
anthropic_service.py
Fallback for frontend generation if Gemini is unavailable.
"""
import asyncio
import re
from typing import AsyncGenerator
from anthropic import AsyncAnthropic
from app.config import settings

# Import system prompts directly from gemini_service to avoid duplication
from app.services.gemini_service import (
    WEBSITE_SYSTEM,
    REFINE_SYSTEM,
    FULLSTACK_FRONTEND_SYSTEM
)

client = None
if settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("your-"):
    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    except Exception as e:
        print(f"[anthropic_service] Failed to init client: {e}")

def is_anthropic_configured() -> bool:
    return client is not None

async def _anthropic_stream(system: str, user: str) -> AsyncGenerator[str, None]:
    if not is_anthropic_configured() or not client:
        yield "<!-- Anthropic API key not configured -->"
        return

    try:
        print("[anthropic_service] Starting stream...")
        stream = await client.messages.create(
            max_tokens=8192,
            messages=[
                {"role": "user", "content": user}
            ],
            model="claude-3-5-sonnet-latest",
            system=system,
            stream=True,
        )

        async for event in stream:
            if event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    yield event.delta.text
    except Exception as e:
        print(f"[anthropic_service] Error: {e}")
        yield f"<!-- Error: {e} -->"

async def stream_website_anthropic(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = (
        f"Build a premium, high-quality UI for: {prompt}. "
        "Ensure it precisely matches the requested layout and functionality. Output ONLY raw HTML."
    )
    async for chunk in _anthropic_stream(WEBSITE_SYSTEM, user_msg):
        yield chunk

async def stream_refine_anthropic(current_code: str, prompt: str) -> AsyncGenerator[str, None]:
    user_msg = f"EXISTING HTML:\n{current_code}\n\nUSER REQUEST:\n{prompt}"
    async for chunk in _anthropic_stream(REFINE_SYSTEM, user_msg):
        yield chunk

async def stream_fullstack_frontend_anthropic(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = (
        f"Build a complete, production-grade web application frontend for: {prompt}. "
        "Make it feel extremely premium and polished. "
        "Include realistic mock data. "
        "IMPORTANT: Start your response IMMEDIATELY with <!DOCTYPE html>. "
        "Do NOT include any text, planning, scratchpad, or explanation before the HTML. "
        "You MUST include Babel Standalone script and use <script type=\"text/babel\"> for your React/JSX code. "
        "Output ONLY the raw HTML file."
    )
    preamble_done = False
    buffer = ''

    async for chunk in _anthropic_stream(FULLSTACK_FRONTEND_SYSTEM, user_msg):
        if preamble_done:
            yield chunk
        else:
            buffer += chunk
            match = re.search(r'(?i)(<!doctype\s+html|<html|<!)', buffer)
            if match:
                preamble_done = True
                yield buffer[match.start():]
            elif len(buffer) > 500:
                preamble_done = True
                yield buffer
