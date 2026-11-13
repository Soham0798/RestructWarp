"""
anthropic_service.py
Primary engine for frontend generation (website, refine, fullstack frontend, visual builder).
Gemini / OpenAI are the fallbacks, wired up in app/routers/generate.py.
"""
import re
from typing import AsyncGenerator

import anthropic
from anthropic import AsyncAnthropic

from app.config import settings

# Prompts are shared with the other providers
from app.services.gemini_service import (
    WEBSITE_SYSTEM,
    REFINE_SYSTEM,
    FULLSTACK_FRONTEND_SYSTEM,
    REACT_BUILDER_SYSTEM,
)

MODEL = "claude-opus-5-5"
EFFORT = "medium"        # low | medium | high | xhigh | max — higher = better output, slower first token
MAX_TOKENS = 64000

client = None
if settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("your-"):
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def is_anthropic_configured() -> bool:
    return client is not None


async def _anthropic_stream(system: str, user: str) -> AsyncGenerator[str, None]:
    """Streams text tokens from Claude.

    Raises if the request fails before any text is produced, so the caller can
    fall back to another provider. A failure mid-stream is yielded as an HTML comment.
    """
    if client is None:
        raise RuntimeError("Anthropic API key not configured")

    print(f"[anthropic_service] Starting stream ({MODEL}, effort={EFFORT})...")
    started = False
    try:
        async with client.beta.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            thinking={"type": "adaptive"},
            output_config={"effort": EFFORT},
            # If Claude's safety classifiers decline a request, the API re-runs it
            # on a fallback Claude model inside the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            async for text in stream.text_stream:
                started = True
                yield text
            final = await stream.get_final_message()

        if final.stop_reason == "refusal":
            if not started:
                raise RuntimeError("Claude declined this request")
            yield "<!-- Error: Claude stopped this response early -->"
        elif final.stop_reason == "max_tokens":
            print("[anthropic_service] WARNING: output hit max_tokens and was truncated")
        print(f"[anthropic_service] Done. stop_reason={final.stop_reason} usage={final.usage.output_tokens} output tokens")
    except anthropic.APIError as e:
        print(f"[anthropic_service] Error: {e}")
        if not started:
            raise
        yield f"<!-- Error: {e} -->"


async def _skip_preamble(chunks: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """Drops any text the model writes before the HTML document starts."""
    preamble_done = False
    buffer = ''
    async for chunk in chunks:
        if preamble_done:
            yield chunk
            continue
        buffer += chunk
        match = re.search(r'(?i)(<!doctype\s+html|<html|<!)', buffer)
        if match:
            preamble_done = True
            yield buffer[match.start():]
        elif len(buffer) > 500:
            preamble_done = True
            yield buffer
    if not preamble_done and buffer:
        yield buffer


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
    async for chunk in _skip_preamble(_anthropic_stream(FULLSTACK_FRONTEND_SYSTEM, user_msg)):
        yield chunk


async def stream_react_builder_anthropic(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = f"BUILDER STATE:\n{prompt}"
    async for chunk in _skip_preamble(_anthropic_stream(REACT_BUILDER_SYSTEM, user_msg)):
        yield chunk
