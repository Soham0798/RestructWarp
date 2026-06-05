"""
groq_service.py
Primary provider for BACKEND generation tasks (FastAPI, Python, etc.).
This service should NOT be used for frontend generation anymore (moved to Claude/DeepSeek).
"""
import time
import asyncio
from functools import partial
from openai import OpenAI
from app.config import settings
import re
import json

def extract_code_block(text: str) -> str:
    """Extracts content from markdown code blocks or returns raw text."""
    pattern = r"```(?:html|javascript|js|jsx|python|py|json)?\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

# Synchronous OpenAI client configured for Groq
client = OpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


def _sync_call(model: str, messages: list, temperature: float = 0.7,
               max_tokens: int = 8192, response_format: dict | None = None) -> str:
    """Run a synchronous Groq API call and return the content string."""
    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if response_format:
        kwargs["response_format"] = response_format
    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content


async def _async_call(model: str, messages: list, temperature: float = 0.7,
                      max_tokens: int = 8192, response_format: dict | None = None) -> str:
    """Run a sync Groq call in a thread executor so it doesn't block the event loop."""
    try:
        loop = asyncio.get_event_loop()
        fn = partial(_sync_call, model, messages, temperature, max_tokens, response_format)
        return await loop.run_in_executor(None, fn)
    except Exception as e:
        err_msg = str(e).lower()
        if "403" in err_msg or "permission" in err_msg or "credit" in err_msg or "rate_limit" in err_msg:
            print(f"[MOCK FALLBACK] Caught Groq Error (Quota/Rate Limit). Returning dummy data. Error: {e}")
            if response_format and response_format.get("type") == "json_object":
                # Mock a backend project payload
                return '''{"requirements.txt": "fastapi==0.104.1", "app/main.py": "from fastapi import FastAPI\\napp = FastAPI()\\n\\n@app.get('/')\\ndef root():\\n    return {'hello': 'world'}"}'''
            # Mock an HTML front-end payload
            return '''```html
<!DOCTYPE html>
<html>
<head>
    <title>Mock Generated Site due to API Limit</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen">
    <div class="text-center p-10 bg-gray-800 rounded-lg shadow-xl">
        <h1 class="text-4xl font-bold mb-4">API Billing Empty ⚠️</h1>
        <p class="text-gray-400">This is a mock response because the Groq API requires credits or has reached its rate limit.</p>
        <p class="mt-4 text-sm text-gray-500">Your backend requested this page through a fallback handler!</p>
    </div>
</body>
</html>
```'''
        raise e



# ─── Public Generation Functions ───

async def generate_text(prompt: str):
    start = time.time()
    content = await _async_call(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1024,
    )
    return content, int((time.time() - start) * 1000)


async def generate_website(prompt: str):
    start = time.time()

    system_prompt = """You are a World-Class Senior Frontend Engineer and UI/UX Designer.
Your goal is to build a premium, expensive-looking, and highly polished UI that perfectly matches the user's request.

### 1. CRITICAL CSS INSTRUCTION
Rewrite the entire app as a single self-contained HTML file with ALL CSS written inside a <style> tag in the <head> — no external stylesheets, no CDN links, no separate .css files, no Tailwind or any framework that requires a build step.
Every single style must be written in raw vanilla CSS inside that one <style> block. Verify that every element — every div, section, nav, button, card, icon, input, and container — has explicit CSS rules covering: background-color, color, font-family, padding, margin, display, width, height, border-radius, and position where applicable.
The final output must open perfectly in any browser with zero internet connection and render as a fully styled, visually polished UI.

### 2. DESIGN SYSTEM (Vanilla CSS)
- **Typography**: system-ui, -apple-system, BlinkMacSystemFont, sans-serif.
- **Colors**: Use a refined palette that fits the requested theme.
- **Effects**: Modern UI trends like glassmorphism, deep shadows, and gradients where appropriate.

### 3. COMPOSITION (Layout)
- Construct the layout and structure strictly based on the user's specific request.
- Do NOT force a generic landing page layout unless requested. If the user asks for a dashboard, build a dashboard. If they ask for a media player, build a media player structure.

### 4. INTERACTIVITY
- **Hover**: Add CSS hover states with `transform: translateY(-5px)`, shadow changes, and `transition: all 0.3s ease`.

### OUTPUT FORMAT
- Return ONLY valid HTML5 code.
- Do NOT include Tailwind.
- Do NOT include FontAwesome or external Google Fonts.
- Place ALL styling within `<style>` in the `<head>`.
"""

    content = await _async_call(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Build a premium, high-quality UI for: {prompt}. Ensure it precisely matches the requested layout."}
        ],
        temperature=0.7,
        max_tokens=8192,
    )

    output = extract_code_block(content)
    return output, int((time.time() - start) * 1000)


async def generate_backend_code(prompt: str):
    start = time.time()

    system_prompt = """You are a Principal Software Architect.
Your task is to generate a comprehensive **FastAPI Backend Project** with multiple files.
You MUST return a valid JSON object where keys are file paths and values are the code content.

### PROJECT STRUCTURE
1. `requirements.txt`: List dependencies (fastapi, uvicorn, sqlalchemy, pydantic, python-jose[cryptography], passlib[bcrypt], multipart).
2. `app/database.py`: SQLAlchemy setup (Base, engine, SessionLocal, get_db).
3. `app/models.py`: SQLAlchemy models (User, and domain specific models).
4. `app/schemas.py`: Pydantic schemas (UserCreate, Token, domain schemas).
5. `app/auth.py`: JWT logic, login endpoint, register endpoint, get_current_user dependency.
6. `app/main.py`: App initialization, include routers, CORS setup (allow *).

### REQUIREMENTS
- **Database**: `sqlite:///./app.db`.
- **Auth**: Implement full JWT auth flow.
- **Business Logic**: Implement CRUD for the user's requested domain in `main.py` (or a separate router file if you prefer).
- **Seeding**: In `main.py`, add `@app.on_event("startup")` to create initial data if tables are empty.

### OUTPUT FORMAT
- Return ONLY the raw JSON string. Do not include markdown formatting like ```json ... ```.
- Example:
{
  "requirements.txt": "fastapi...",
  "app/main.py": "from fastapi import..."
}
"""

    content = await _async_call(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate a multi-file FastAPI project for: {prompt}. Return JSON only."}
        ],
        temperature=0.5,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    json_str = extract_code_block(content)
    try:
        project_dict = json.loads(json_str)
        return project_dict, int((time.time() - start) * 1000)
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw": content}, int((time.time() - start) * 1000)


async def generate_functional_frontend(prompt: str):
    start = time.time()

    system_prompt = """You are a Senior Frontend Architect.
Your task is to generate a **Complex, Production-Grade React Application**.

### OUTPUT FORMAT: JSON
Return a JSON object with TWO keys:
1. `files`: A dictionary of file paths and code (Standard React Project structure).
   - Must include: `src/App.jsx`, `src/main.jsx`, `src/components/...` (Sidebar, Navbar, Cards), `src/pages/...` (Dashboard, Login, Settings).
   - Use `import` and `export` syntax.
   - Separate concerns (logic, UI, data fetching).
   - Use `axios` or `fetch` for API calls to `http://localhost:8000`.
   - Use **Tailwind CSS** for styling (glassmorphism, premium feel, dark mode).
2. `preview`: A SINGLE STRING containing the ENTIRE application for a Live Demo.
   - **NO** `import` or `export` statements.
   - Concatenate all components (App, Sidebar, Pages) into this one string so it can run in a browser script tag.
   - Your HTML string MUST include ALL THREE scripts: React 18, ReactDOM 18, AND Babel Standalone (https://unpkg.com/@babel/standalone/babel.min.js).
   - Your main application code MUST be inside a `<script type="text/babel">` tag.
   - Without type="text/babel", JSX syntax will NOT work and the page will be blank.
   - End with `const root = ReactDOM.createRoot(document.getElementById('root')); root.render(<App />);`.

### REQUIREMENTS
- **Complexity**: Multiple pages (Dashboard, Settings, User Profile), complex UI components (DataTables, Modal, Forms).
- **Navigation**: Use <button> for internal links, OR if using <a href="#">, you MUST call e.preventDefault() in the onClick handler so the host platform does not reload.
- **Data**: Fetch real data from backend, fallback to mock data if failed.
- **Styling**: Premium, polished UI.
- **DARK MODE ONLY**: You MUST ALWAYS use a dark theme. Body/root background must be dark (#0a0c12, #0f172a, #111827). ALL text must be light/white (#e2e8f0, #f1f5f9). Cards use slightly lighter dark shades (#1e293b). NEVER use white/light backgrounds. NEVER use dark text on dark backgrounds.

### EXAMPLE JSON Structure
{
  "files": {
    "src/App.jsx": "import React from 'react';...",
    "src/components/Header.jsx": "export default function Header()..."
  },
  "preview": "<!DOCTYPE html><html><head><script src='https://unpkg.com/react@18/umd/react.development.js'></script><script src='https://unpkg.com/react-dom@18/umd/react-dom.development.js'></script><script src='https://unpkg.com/@babel/standalone/babel.min.js'></script></head><body><div id='root'></div><script type='text/babel'>const Header = () => <div>...</div>; const App = () => <Header />; const root = ReactDOM.createRoot(document.getElementById('root')); root.render(<App />);</script></body></html>"
}
"""

    content = await _async_call(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Build a complex React app for: {prompt}. Connect to localhost:8000. Return JSON."}
        ],
        temperature=0.7,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    json_str = extract_code_block(content)
    try:
        data = json.loads(json_str)
        return data, int((time.time() - start) * 1000)
    except Exception:
        return {"preview": "// Failed to generate complex structure. Please try again.", "files": {}}, int((time.time() - start) * 1000)


async def generate_fullstack(prompt: str):
    start = time.time()
    # Run both in parallel since they are now truly async (thread executor)
    frontend_task = generate_functional_frontend(prompt)
    backend_task = generate_backend_code(prompt)

    (frontend_code, _), (backend_code, _) = await asyncio.gather(frontend_task, backend_task)

    return {
        "frontend": frontend_code,
        "backend": backend_code
    }, int((time.time() - start) * 1000)


async def refine_website(current_code: str, prompt: str):
    start = time.time()

    system_prompt = """You are an expert AI Web Developer. Edit the provided HTML based on the user's request.
The app is rendering but looks visually broken and unpolished. Fix all of the following issues without changing the core design, color scheme, or layout structure:

Placeholder text showing inside visual containers — Any element that is meant to display a visual (image, avatar, thumbnail, cover, icon, illustration) must never show raw text like "Image", "Photo", "Thumbnail", "Avatar", "Icon" etc. inside it. Remove all such text. Replace every visual container with a styled CSS block using a linear-gradient, a background color, or an inline SVG icon. The container must have explicit width, height, border-radius, and display: block so it renders as a visible styled shape.
Broken flex layouts in cards and list rows — Every card, row, or list item that contains a visual on the left and text on the right must use display: flex; align-items: center; gap: 12px. Nothing inside a card should stack vertically unless it is explicitly meant to. Text must never wrap awkwardly or overflow its container. Add white-space: nowrap; overflow: hidden; text-overflow: ellipsis to all single-line text labels.
Fixed bars are incomplete — Any fixed header, bottom bar, or footer must be divided into three sections (left, center, right) using display: flex; justify-content: space-between; align-items: center. Each section must contain all its intended elements — labels, buttons, sliders, icons. Nothing should be missing, collapsed, or invisible.
Section labels are too large or wrapping — Any label that is meant to be a small uppercase category title must be styled as: font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; white-space: nowrap. It must never wrap onto multiple lines or appear at heading size.
Visual containers are wrong aspect ratio — Any container meant to be square (thumbnail, avatar, card cover) must use either matching width and height values or aspect-ratio: 1 / 1. No visual block should appear as a tall rectangle, flat strip, or collapsed zero-height element.
Spacing is cramped or inconsistent — Add gap: 16px to every flex and grid container. Add padding: 24px to the main scrollable content area. Every section heading needs margin-bottom: 16px. No two elements should be touching without at least 8px of space between them.
Empty or invisible sections — If a section of the layout appears completely empty or blank, it means a child element failed to render. Add a visible placeholder using a gradient block, a simple icon, or dummy text so no section of the UI appears broken or forgotten.

Output one single self-contained HTML file. All CSS must be inside a <style> tag in the <head>. No external files, no CDN links, no frameworks requiring a build step.
Return ONLY the complete updated raw HTML. No markdown, no explanation."""

    user_message = f"""
HTML:
{current_code}

Request: {prompt}
"""

    content = await _async_call(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=8192,
    )

    output = extract_code_block(content)
    return output, int((time.time() - start) * 1000)

# ─── OpenAI Streaming (Fallback) ───

from typing import AsyncGenerator
from app.services.gemini_service import WEBSITE_SYSTEM, REFINE_SYSTEM, FULLSTACK_FRONTEND_SYSTEM

async def _openai_stream(system: str, user: str) -> AsyncGenerator[str, None]:
    try:
        from openai import AsyncOpenAI
        
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise Exception("OpenAI API key not configured in .env file (using for OpenRouter)")
            
        async with AsyncOpenAI(
            api_key=api_key, 
            base_url="https://openrouter.ai/api/v1",
        ) as async_client:
            # Guide the reasoning model to plan and think deeply
            thinking_prompt = (
                "[THINKING PROCESS REQUESTED]\n"
                "Analyze the following request step-by-step. Use deep reasoning to plan the layout, "
                "responsive behavior, component state management, and Tailwind styling before outputting any code. "
                "Generate a highly complete, professional-grade interface without any placeholder text or mock omissions.\n\n"
            )
            full_user_prompt = thinking_prompt + user

            stream = await async_client.chat.completions.create(
                model="openai/o3-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_user_prompt}
                ],
                stream=True,
                max_completion_tokens=8192
            )
        
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
    except Exception as e:
        print(f"[openai_stream] Error: {e}")
        yield f"<!-- Error: {e} -->"

async def stream_website_openai(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = (
        f"Build a premium, high-quality UI for: {prompt}. "
        "Ensure it precisely matches the requested layout and functionality. Output ONLY raw HTML. No markdown code blocks."
    )
    async for chunk in _openai_stream(WEBSITE_SYSTEM, user_msg):
        yield chunk

async def stream_refine_openai(current_code: str, prompt: str) -> AsyncGenerator[str, None]:
    user_msg = f"EXISTING HTML:\n{current_code}\n\nUSER REQUEST:\n{prompt}\n\nOutput ONLY raw HTML. No markdown code blocks."
    async for chunk in _openai_stream(REFINE_SYSTEM, user_msg):
        yield chunk

async def stream_fullstack_frontend_openai(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = (
        f"Build a complete, production-grade web application frontend for: {prompt}. "
        "Make it feel extremely premium and polished. "
        "Include realistic mock data. "
        "IMPORTANT: Start your response IMMEDIATELY with <!DOCTYPE html>. "
        "Do NOT include any text, planning, scratchpad, or explanation before the HTML. "
        "You MUST include Babel Standalone script and use <script type=\"text/babel\"> for your React/JSX code. "
        "Output ONLY the raw HTML file. No markdown code blocks."
    )
    preamble_done = False
    buffer = ''

    async for chunk in _openai_stream(FULLSTACK_FRONTEND_SYSTEM, user_msg):
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

# ─── NVIDIA NIM Streaming (Fallback 2) ───

async def _nvidia_stream(system: str, user: str) -> AsyncGenerator[str, None]:
    try:
        from openai import AsyncOpenAI
        
        api_key = settings.NVIDIA_API_KEY
        if not api_key:
            raise Exception("NVIDIA API key not configured in .env file")
            
        async with AsyncOpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1"
        ) as async_client:
            stream = await async_client.chat.completions.create(
                model="meta/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                stream=True,
                max_tokens=4096,
                temperature=0.7
            )
        
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
    except Exception as e:
        print(f"[nvidia_stream] Error: {e}")
        yield f"<!-- Error: {e} -->"

async def stream_fullstack_frontend_nvidia(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = (
        f"Build a complete, production-grade web application frontend for: {prompt}. "
        "Make it feel extremely premium and polished. "
        "Include realistic mock data. "
        "IMPORTANT: Start your response IMMEDIATELY with <!DOCTYPE html>. "
        "Do NOT include any text, planning, scratchpad, or explanation before the HTML. "
        "You MUST include Babel Standalone script and use <script type=\"text/babel\"> for your React/JSX code. "
        "Output ONLY the raw HTML file. No markdown code blocks."
    )
    preamble_done = False
    buffer = ''

    async for chunk in _nvidia_stream(FULLSTACK_FRONTEND_SYSTEM, user_msg):
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
