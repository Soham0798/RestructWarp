import asyncio
import json
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy.future import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.generation import Generation
from app.security.jwt_handler import verify_token
from app.schemas.generate_schema import GenerateSchema
from app.services.anthropic_service import (
    stream_website_anthropic, stream_refine_anthropic,
    stream_fullstack_frontend_anthropic, stream_react_builder_anthropic,
    is_anthropic_configured,
)
from app.services.gemini_service import (
    stream_website_gemini, stream_refine_gemini,
    stream_fullstack_frontend_gemini, is_gemini_configured,
    stream_react_builder_gemini
)
from app.services.groq_service import (
    generate_text, generate_backend_code, extract_code_block,
    stream_website_openai, stream_refine_openai,
    stream_fullstack_frontend_openai,
    stream_fullstack_frontend_nvidia,
    stream_react_builder_openai
)
from app.services.credit_service import deduct_credit

router = APIRouter(prefix="/generate")
security = HTTPBearer()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _require_payload(credentials: HTTPAuthorizationCredentials) -> dict:
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


# Frontend generation engines, tried in order: Claude (primary) -> Gemini -> OpenAI (-> NVIDIA).
FRONTEND_PROVIDERS = {
    "website": [
        ("claude", stream_website_anthropic),
        ("gemini", stream_website_gemini),
        ("openai", stream_website_openai),
    ],
    "refine": [
        ("claude", stream_refine_anthropic),
        ("gemini", stream_refine_gemini),
        ("openai", stream_refine_openai),
    ],
    "fullstack": [
        ("claude", stream_fullstack_frontend_anthropic),
        ("gemini", stream_fullstack_frontend_gemini),
        ("openai", stream_fullstack_frontend_openai),
        ("nvidia", stream_fullstack_frontend_nvidia),
    ],
    "react_builder": [
        ("claude", stream_react_builder_anthropic),
        ("gemini", stream_react_builder_gemini),
        ("openai", stream_react_builder_openai),
    ],
}


async def _stream_frontend(kind: str, *args) -> AsyncGenerator[str, None]:
    """Streams tokens from the first engine that starts producing output.

    An engine that fails before its first token is skipped and the next one is tried.
    """
    last_error = None
    for name, make_stream in FRONTEND_PROVIDERS[kind]:
        if name == "claude" and not is_anthropic_configured():
            continue
        try:
            iterator = make_stream(*args)
            first_token = await iterator.__anext__()
            if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                raise Exception(first_token)
        except Exception as e:
            print(f"[generate.py] {name} failed for {kind}, trying next engine: {e!r}")
            last_error = e
            continue

        yield first_token
        async for token in iterator:
            yield token
        return

    raise Exception(f"All AI engines failed. Last error: {last_error}")


async def _collect_frontend(kind: str, *args) -> str:
    return "".join([token async for token in _stream_frontend(kind, *args)])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Access-Control-Allow-Origin": "*",
}


# ─── POST /generate/stream  (streaming generation) ───────────────────────────

@router.post("/stream")
async def generate_stream(
    data: GenerateSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Streams generation token-by-token.
    SSE format: `data: {"chunk": "...token..."}\n\n`
    Ends with:  `data: [DONE]\n\n`
    On error:   `data: {"error": "..."}\n\n`
    """
    payload = _require_payload(credentials)

    # Collect chunks so we can persist after streaming completes
    chunks: list[str] = []
    start_time = time.time()

    async def event_stream():
        try:
            if data.type in ("website", "react_builder"):
                async for token in _stream_frontend(data.type, data.prompt):
                    chunks.append(token)
                    yield _sse({'chunk': token})

            elif data.type == "fullstack":
                # Sequential Generation: Backend First -> Frontend Second

                # 1. Start Groq backend generation as a background task
                backend_task = asyncio.create_task(generate_backend_code(data.prompt))

                yield _sse({'chunk': '/* Step 1: Designing Backend API... */\n'})

                # Heartbeat while waiting for backend (prevents timeout & updates UI)
                while not backend_task.done():
                    yield _sse({'chunk': '.'})
                    await asyncio.sleep(1.0)

                try:
                    backend_output, _ = backend_task.result()
                    backend_serialized = (
                        backend_output if isinstance(backend_output, str)
                        else json.dumps(backend_output)
                    )
                except Exception as be:
                    yield _sse({'backend_error': str(be)})
                    # If backend fails, we stop the stream
                    return

                yield _sse({'chunk': '\n\n/* Backend Complete.\n   Step 2: Building Frontend... */\n\n'})

                # 2. Inject Backend Spec into Frontend Prompt
                enriched_prompt = (
                    f"{data.prompt}\n\n"
                    "CRITICAL: The backend for this application has already been generated. "
                    "You MUST use the following backend API specification to ensure your frontend fetch calls exactly match the available endpoints and data structures.\n\n"
                    f"--- BACKEND API SPECIFICATION ---\n{backend_serialized}\n---------------------------------\n"
                )

                # 3. Stream frontend tokens in real-time
                frontend_html = []
                async for token in _stream_frontend("fullstack", enriched_prompt):
                    frontend_html.append(token)
                    chunks.append(token)
                    yield _sse({'chunk': token})

                # Frontend done — send the preview HTML as a separate event
                yield _sse({'preview': "".join(frontend_html)})

                # Send the backend payload at the end for the code viewer tab
                chunks.append(backend_serialized)
                yield _sse({'backend_payload': backend_serialized})

            elif data.type == "backend":
                # Groq generates backend; send the full payload when done
                output, _ = await generate_backend_code(data.prompt)
                serialized = output if isinstance(output, str) else json.dumps(output)
                chunks.append(serialized)
                yield _sse({'payload': serialized, 'output_type': 'backend'})

            else:
                output, _ = await generate_text(data.prompt)
                serialized = output if isinstance(output, str) else json.dumps(output)
                chunks.append(serialized)
                yield _sse({'payload': serialized, 'output_type': data.type})

        except Exception as e:
            yield _sse({'error': str(e)})
        finally:
            yield "data: [DONE]\n\n"

    async def _save_to_db():
        """Runs after streaming completes (background task)."""
        full_output = "".join(chunks)
        response_ms = int((time.time() - start_time) * 1000)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.id == payload["user_id"])
                )
                user = result.scalar_one_or_none()
                if user:
                    await deduct_credit(db, user)
                    gen = Generation(
                        user_id=user.id,
                        prompt=data.prompt,
                        output=extract_code_block(full_output) if data.type == "website" else full_output,
                        type=data.type,
                        response_time=response_ms,
                    )
                    db.add(gen)
                    await db.commit()
        except Exception as e:
            print(f"[ERROR] Failed to save generation: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
        background=BackgroundTask(_save_to_db),
    )


# ─── POST /generate/refine-stream  (streaming refine) ────────────────────────

@router.post("/refine-stream")
async def refine_stream(
    data: GenerateSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = _require_payload(credentials)

    if not data.current_code:
        raise HTTPException(status_code=400, detail="Missing current_code for refinement")

    chunks: list[str] = []
    start_time = time.time()

    async def event_stream():
        try:
            async for token in _stream_frontend("refine", data.current_code, data.prompt):
                chunks.append(token)
                yield _sse({'chunk': token})
        except Exception as e:
            yield _sse({'error': str(e)})
        finally:
            yield "data: [DONE]\n\n"

    async def _save_to_db():
        full_output = "".join(chunks)
        response_ms = int((time.time() - start_time) * 1000)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.id == payload["user_id"])
                )
                user = result.scalar_one_or_none()
                if user:
                    await deduct_credit(db, user)
                    gen = Generation(
                        user_id=user.id,
                        prompt=f"[Refine] {data.prompt}",
                        output=extract_code_block(full_output),
                        type="website",
                        response_time=response_ms,
                    )
                    db.add(gen)
                    await db.commit()
        except Exception as e:
            print(f"[ERROR] Failed to save refinement: {e}")

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
        background=BackgroundTask(_save_to_db),
    )


# ─── GET /generate/status  (which AI engine is active) ───────────────────────

@router.get("/status")
async def generation_status():
    """
    Returns the status of the AI generation engines.
    Frontend: Claude (Primary) -> Gemini -> OpenAI (Fallbacks)
    Backend: Groq (Exclusive)
    """
    claude_ok = is_anthropic_configured()
    gemini_ok = is_gemini_configured()
    openai_ok = bool(settings.OPENAI_API_KEY)

    if claude_ok:
        engine = "claude"
    elif gemini_ok:
        engine = "gemini"
    elif openai_ok:
        engine = "openai"
    else:
        engine = "groq"

    return {
        "engine": engine,
        "claude_available": claude_ok,
        "gemini_available": gemini_ok,
        "openai_available": openai_ok,
        "groq_available": True,  # Always available for backend
        "streaming": True,
    }


# ─── POST /generate/refine  (legacy non-streaming refine) ────────────────────

@router.post("/refine")
async def refine(
    data: GenerateSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = _require_payload(credentials)

    if not data.current_code:
        raise HTTPException(status_code=400, detail="Missing current_code for refinement")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == payload["user_id"]))
        user = result.scalar_one()

        start_time_ts = time.time()
        output = await _collect_frontend("refine", data.current_code, data.prompt)
        response_time = int((time.time() - start_time_ts) * 1000)

        await deduct_credit(db, user)

        gen = Generation(
            user_id=user.id,
            prompt=f"Refine: {data.prompt}",
            output=extract_code_block(output),
            type="website",
            response_time=response_time,
        )
        db.add(gen)
        await db.commit()

    return {"output": output, "response_time_ms": response_time}


# ─── POST /generate/  (legacy non-streaming generation) ──────────────────────

@router.post("/")
async def generate(
    data: GenerateSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    print(f"DEBUG: generation request type='{data.type}' prompt='{data.prompt[:60]}'")

    payload = _require_payload(credentials)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == payload["user_id"]))
        user = result.scalar_one()

        st = time.time()
        if data.type in ("website", "react_builder"):
            output = await _collect_frontend(data.type, data.prompt)
            response_time = int((time.time() - st) * 1000)
            db_output = extract_code_block(output)
        elif data.type == "backend":
            # Use Groq for backend
            output, response_time = await generate_backend_code(data.prompt)
            db_output = output if isinstance(output, str) else json.dumps(output)
        elif data.type == "fullstack":
            # Frontend engine and Groq backend run in parallel
            frontend_html, (backend_code, _) = await asyncio.gather(
                _collect_frontend("fullstack", data.prompt),
                generate_backend_code(data.prompt),
            )
            output = {
                "frontend": {"preview": frontend_html, "files": {}},  # Legacy structure
                "backend": backend_code
            }
            response_time = int((time.time() - st) * 1000)
            db_output = json.dumps(output)
        else:
            output, response_time = await generate_text(data.prompt)
            db_output = output if isinstance(output, str) else json.dumps(output)

        await deduct_credit(db, user)

        gen = Generation(
            user_id=user.id,
            prompt=data.prompt,
            output=db_output,
            type=data.type,
            response_time=response_time,
        )
        db.add(gen)
        await db.commit()

    return {"output": output, "response_time_ms": response_time}
