"""One door to the LLM (Step 24).

Primary: Claude (Restruct Warp's main engine), when ANTHROPIC_API_KEY is set.
Fallback: any OpenAI-compatible server, chosen in .env:
  Groq (free tier):  LLM_BASE_URL=https://api.groq.com/openai/v1  + LLM_API_KEY
  Ollama (local):    LLM_BASE_URL=http://localhost:11434/v1        (key can be anything)
"""
import json
import re
from typing import Optional

import logging

import httpx
from openai import APIError, AsyncOpenAI, BadRequestError

from app.config import settings
from app.services import anthropic_service

log = logging.getLogger(__name__)


class LLMUnavailable(RuntimeError):
    """No LLM is configured or it could not be reached; callers fall back to rules."""


def api_key() -> str:
    """LLM_API_KEY if set (even to "", which switches the LLM off); otherwise Restruct Warp's Groq key."""
    if settings.LLM_API_KEY is not None:
        return settings.LLM_API_KEY
    return settings.GROQ_API_KEY if "groq.com" in settings.LLM_BASE_URL else ""


def fallback_configured() -> bool:
    """Is the OpenAI-compatible server (Groq / Ollama) usable?"""
    local = "localhost" in settings.LLM_BASE_URL or "127.0.0.1" in settings.LLM_BASE_URL
    return bool(api_key()) or local


def is_configured() -> bool:
    return anthropic_service.is_anthropic_configured() or fallback_configured()


async def _claude_chat(messages: list[dict]) -> str:
    """OpenAI-style messages -> Claude: system messages become the system prompt."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
    return await anthropic_service.complete(turns, system=system or None)


def make_client(http_client: Optional[httpx.AsyncClient] = None) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=settings.LLM_BASE_URL, api_key=api_key() or "ollama",
                       timeout=60, max_retries=2, http_client=http_client)


async def chat(messages: list[dict], model: Optional[str] = None, json_mode: bool = False,
               client: Optional[AsyncOpenAI] = None) -> str:
    # a client passed in (tests, scripts) or an explicit model means "use the OpenAI-compatible server"
    if client is None and model is None and anthropic_service.is_anthropic_configured():
        try:
            return await _claude_chat(messages)
        except Exception as e:
            if not fallback_configured():
                raise LLMUnavailable(str(e)) from e
            log.warning("Claude failed, falling back to %s: %s", settings.LLM_BASE_URL, str(e)[:200])
    if client is None and not fallback_configured():
        raise LLMUnavailable("Set ANTHROPIC_API_KEY, or LLM_API_KEY (Groq), or point LLM_BASE_URL at Ollama")
    client = client or make_client()
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    model = model or settings.LLM_CODE_MODEL
    try:
        try:
            res = await client.chat.completions.create(model=model, messages=messages, temperature=0.2, **kwargs)
        except BadRequestError as e:
            if not (json_mode and "json" in str(e).lower()):
                raise
            # Groq's strict JSON mode gives up on long documents; extract_json copes with a plain reply
            res = await client.chat.completions.create(model=model, messages=messages, temperature=0.2)
    except (APIError, httpx.HTTPError) as e:
        raise LLMUnavailable(str(e)) from e
    return res.choices[0].message.content or ""


def extract_json(text: str) -> dict:
    """Parse JSON from a reply, tolerating ```json fences or chatter around it."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    raw = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)
