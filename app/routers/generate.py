import json
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.generation import Generation
from app.security.jwt_handler import verify_token
from app.schemas.generate_schema import GenerateSchema
from app.services.groq_service import (
    generate_text, generate_website, refine_website,
    generate_backend_code, generate_fullstack, extract_code_block
)
from app.services.gemini_service import (
    stream_website_gemini, stream_refine_gemini,
    stream_fullstack_frontend_gemini, is_gemini_configured
)
from app.services.groq_service import (
    generate_text, generate_website, refine_website,
    generate_backend_code, generate_fullstack, extract_code_block,
    stream_website_openai, stream_refine_openai,
    stream_fullstack_frontend_openai,
    stream_fullstack_frontend_nvidia
)
from app.services.credit_service import deduct_credit

router = APIRouter(prefix="/generate")
security = HTTPBearer()


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_user(payload: dict) -> User | None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == payload["user_id"]))
        return result.scalar_one_or_none()


def _require_payload(credentials: HTTPAuthorizationCredentials) -> dict:
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


# ─── POST /generate/stream  (Claude streaming – website) ─────────────────────

@router.post("/stream")
async def generate_stream(
    data: GenerateSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Streams HTML generation token-by-token using Claude.
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
            if data.type == "website":
                # True token-by-token streaming for websites
                try:
                    iterator = stream_website_gemini(data.prompt)
                    first_token = await iterator.__anext__()
                    
                    if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                        raise Exception(first_token)
                        
                    chunks.append(first_token)
                    yield f"data: {json.dumps({'chunk': first_token})}\n\n"
                    
                    async for token in iterator:
                        chunks.append(token)
                        yield f"data: {json.dumps({'chunk': token})}\n\n"
                except Exception as e:
                    print(f"[generate.py] Gemini failed, falling back to OpenAI for website: {e}")
                    async for token in stream_website_openai(data.prompt):
                        chunks.append(token)
                        yield f"data: {json.dumps({'chunk': token})}\n\n"

            elif data.type == "fullstack":
                # Sequential Generation: Backend First -> Frontend Second
                import asyncio
                
                # 1. Start Groq backend generation as a background task
                backend_task = asyncio.create_task(generate_backend_code(data.prompt))
                
                # Yield initial status
                yield f"data: {json.dumps({'chunk': '/* Step 1: Designing Backend API... */\\n'})}\n\n"
                
                # Heartbeat while waiting for backend (prevents timeout & updates UI)
                while not backend_task.done():
                    yield f"data: {json.dumps({'chunk': '.'})}\n\n"
                    await asyncio.sleep(1.0)
                    
                # Backend complete
                try:
                    backend_output, _ = backend_task.result()
                    backend_serialized = (
                        backend_output if isinstance(backend_output, str)
                        else json.dumps(backend_output)
                    )
                except Exception as be:
                    yield f"data: {json.dumps({'backend_error': str(be)})}\n\n"
                    # If backend fails, we stop the stream
                    return
                
                yield f"data: {json.dumps({'chunk': '\\n\\n/* Backend Complete.\\n   Step 2: Building Frontend... */\\n\\n'})}\n\n"
                
                # 2. Inject Backend Spec into Frontend Prompt
                enriched_prompt = (
                    f"{data.prompt}\n\n"
                    "CRITICAL: The backend for this application has already been generated. "
                    "You MUST use the following backend API specification to ensure your frontend fetch calls exactly match the available endpoints and data structures.\n\n"
                    f"--- BACKEND API SPECIFICATION ---\n{backend_serialized}\n---------------------------------\n"
                )

                # 3. Stream Gemini frontend tokens in real-time
                frontend_html = []
                try:
                    iterator = stream_fullstack_frontend_gemini(enriched_prompt)
                    first_token = await iterator.__anext__()
                    
                    if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                        raise Exception(first_token)
                        
                    frontend_html.append(first_token)
                    chunks.append(first_token)
                    yield f"data: {json.dumps({'chunk': first_token})}\n\n"
                    
                    async for token in iterator:
                        frontend_html.append(token)
                        chunks.append(token)
                        yield f"data: {json.dumps({'chunk': token})}\n\n"
                except Exception as e:
                    print(f"[generate.py] Gemini failed, falling back to OpenAI for fullstack: {e}")
                    try:
                        iterator = stream_fullstack_frontend_openai(enriched_prompt)
                        first_token = await iterator.__anext__()
                        if first_token.startswith("<!-- Error:"):
                            raise Exception(first_token)
                            
                        frontend_html.append(first_token)
                        chunks.append(first_token)
                        yield f"data: {json.dumps({'chunk': first_token})}\n\n"
                        
                        async for token in iterator:
                            frontend_html.append(token)
                            chunks.append(token)
                            yield f"data: {json.dumps({'chunk': token})}\n\n"
                    except Exception as e2:
                        print(f"[generate.py] OpenAI failed, falling back to NVIDIA for fullstack: {e2}")
                        async for token in stream_fullstack_frontend_nvidia(enriched_prompt):
                            frontend_html.append(token)
                            chunks.append(token)
                            yield f"data: {json.dumps({'chunk': token})}\n\n"

                # Frontend done — send the preview HTML as a separate event
                preview_html = "".join(frontend_html)
                yield f"data: {json.dumps({'preview': preview_html})}\n\n"

                # Send the backend payload at the end for the code viewer tab
                chunks.append(backend_serialized)
                yield f"data: {json.dumps({'backend_payload': backend_serialized})}\n\n"

            elif data.type == "backend":
                # Groq generates backend; send heartbeat then full payload
                import asyncio
                working = True

                async def _hb():
                    while working:
                        await asyncio.sleep(1)

                hb = asyncio.create_task(_hb())
                try:
                    output, _ = await generate_backend_code(data.prompt)
                finally:
                    working = False
                    hb.cancel()

                serialized = output if isinstance(output, str) else json.dumps(output)
                chunks.append(serialized)
                yield f"data: {json.dumps({'payload': serialized, 'output_type': 'backend'})}\n\n"

            else:
                output, _ = await generate_text(data.prompt)
                serialized = output if isinstance(output, str) else json.dumps(output)
                chunks.append(serialized)
                yield f"data: {json.dumps({'payload': serialized, 'output_type': data.type})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
        background=BackgroundTask(_save_to_db),
    )


# ─── POST /generate/refine-stream  (Claude streaming refine) ─────────────────

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
            try:
                iterator = stream_refine_gemini(data.current_code, data.prompt)
                first_token = await iterator.__anext__()
                
                if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                    raise Exception(first_token)
                    
                chunks.append(first_token)
                yield f"data: {json.dumps({'chunk': first_token})}\n\n"
                
                async for token in iterator:
                    chunks.append(token)
                    yield f"data: {json.dumps({'chunk': token})}\n\n"
            except Exception as e:
                print(f"[generate.py] Gemini failed, falling back to OpenAI for refine: {e}")
                async for token in stream_refine_openai(data.current_code, data.prompt):
                    chunks.append(token)
                    yield f"data: {json.dumps({'chunk': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
        background=BackgroundTask(_save_to_db),
    )


# ─── GET /generate/status  (which AI engine is active) ───────────────────────

@router.get("/status")
async def generation_status():
    """
    Returns the status of the AI generation engines.
    Frontend: Gemini (Primary) -> OpenAI (Fallback)
    Backend: Groq (Exclusive)
    """
    from app.config import settings
    gemini_ok = is_gemini_configured()
    openai_ok = bool(settings.OPENAI_API_KEY) 

    if not gemini_ok:
        return {
            "engine": "openai" if openai_ok else "groq",
            "gemini_available": False,
            "openai_available": openai_ok,
            "groq_available": True, # Always available for backend
            "streaming": True
        }

    return {
        "engine": "gemini",
        "gemini_available": True,
        "openai_available": openai_ok,
        "groq_available": True,
        "streaming": True
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

        # Use streaming service and collect chunks for legacy support
        chunks = []
        start_time_ts = time.time()
        try:
            iterator = stream_refine_gemini(data.current_code, data.prompt)
            first_token = await iterator.__anext__()
            if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                raise Exception(first_token)
            chunks.append(first_token)
            async for chunk in iterator:
                chunks.append(chunk)
        except Exception as e:
            print(f"[generate.py] Gemini failed, falling back to OpenAI for legacy refine: {e}")
            async for chunk in stream_refine_openai(data.current_code, data.prompt):
                chunks.append(chunk)
        
        output = "".join(chunks)
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

        if data.type == "website":
            # Use Gemini for website
            chunks = []
            st = time.time()
            try:
                iterator = stream_website_gemini(data.prompt)
                first_token = await iterator.__anext__()
                if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                    raise Exception(first_token)
                chunks.append(first_token)
                async for chunk in iterator:
                    chunks.append(chunk)
            except Exception as e:
                print(f"[generate.py] Gemini failed, falling back to OpenAI for legacy website: {e}")
                async for chunk in stream_website_openai(data.prompt):
                    chunks.append(chunk)
            output = "".join(chunks)
            response_time = int((time.time() - st) * 1000)
            db_output = extract_code_block(output)
        elif data.type == "backend":
            # Use Groq for backend
            output, response_time = await generate_backend_code(data.prompt)
            db_output = output if isinstance(output, str) else json.dumps(output)
        elif data.type == "fullstack":
            # Use Gemini for frontend and Groq for backend
            import asyncio
            st = time.time()
            
            async def get_frontend():
                chunks = []
                try:
                    iterator = stream_fullstack_frontend_gemini(data.prompt)
                    first_token = await iterator.__anext__()
                    if first_token.startswith("<!-- Error:") or first_token.startswith("<!-- Gemini"):
                        raise Exception(first_token)
                    chunks.append(first_token)
                    async for chunk in iterator:
                        chunks.append(chunk)
                except Exception as e:
                    print(f"[generate.py] Gemini failed, falling back to OpenAI for legacy fullstack: {e}")
                    async for chunk in stream_fullstack_frontend_openai(data.prompt):
                        chunks.append(chunk)
                return "".join(chunks)

            frontend_task = asyncio.create_task(get_frontend())
            backend_task = asyncio.create_task(generate_backend_code(data.prompt))
            
            frontend_html, (backend_code, _) = await asyncio.gather(frontend_task, backend_task)
            
            output = {
                "frontend": {"preview": frontend_html, "files": {}}, # Legacy structure
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
