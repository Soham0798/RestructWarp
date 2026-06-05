"""
gemini_service.py
Real-time streaming generation.
Primary: Google Gemini
"""
import asyncio
import time
import re
from typing import AsyncGenerator
from google import genai
from google.genai import types
from app.config import settings

# Configure Gemini Client
client = None
if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

# ─── Prompts ──────────────────────────────────────────────────────────────────

WEBSITE_SYSTEM = """You are a World-Class Senior Frontend Engineer and UI/UX Designer.
Your goal is to build a premium, expensive-looking, and highly polished UI that perfectly matches the user's request.

CRITICAL CSS INSTRUCTION:
Rewrite the entire app as a single self-contained HTML file with ALL CSS written inside a <style> tag in the <head> — no external stylesheets, no CDN links, no separate .css files, no Tailwind or any framework that requires a build step.
Every single style must be written in raw vanilla CSS inside that one <style> block. Verify that every element — every div, section, nav, button, card, icon, input, and container — has explicit CSS rules covering: background-color, color, font-family, padding, margin, display, width, height, border-radius, and position where applicable.
The final output must be one single .html file that opens perfectly in any browser with zero internet connection and renders as a fully styled, visually polished UI. No broken layouts. No unstyled text. No missing colors.

DESIGN SYSTEM (Vanilla CSS):
- Typography: Use system fonts (system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif) to ensure offline compatibility.
- Colors: Use a refined color palette that fits the requested theme.
- Effects: Modern UI trends like glassmorphism (backdrop-filter: blur, rgba borders), deep shadows, or gradients where appropriate.

LAYOUT INSTRUCTIONS:
- Construct the layout and structure strictly based on the user's specific request.
- Do NOT force a generic landing page layout unless requested. If the user asks for a dashboard, build a dashboard. If they ask for a media player, build a media player structure.

INTERACTIVITY: Add CSS transitions, hover transforms (translateY, scale), and box-shadow changes.

OUTPUT — ONLY raw valid HTML5. No markdown fences. No explanations.
Do NOT include any external <link> or <script> tags for styles or fonts. ALL CSS must be in the <style> tag."""

REFINE_SYSTEM = """You are an expert AI Web Developer. Edit the provided HTML based on the user's request.
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

FULLSTACK_FRONTEND_SYSTEM = """You are a World-Class Senior Full-Stack UI Engineer.
Generate a COMPLETE, PRODUCTION-GRADE frontend application as a single self-contained HTML file.

TECH STACK (all via CDN — NO build step, runs in browser):
- React 18: <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
- ReactDOM 18: <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
- Babel Standalone (REQUIRED for JSX): <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
- Tailwind CSS: <script src="https://cdn.tailwindcss.com"></script>
- Lucide icons: <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
- Font Awesome 6: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
- Google Fonts: Inter, Plus Jakarta Sans

CRITICAL SCRIPT RULES:
- You MUST include ALL THREE scripts: React, ReactDOM, AND Babel Standalone.
- Your main application code MUST be in a <script type="text/babel"> tag (NOT <script> or <script type="text/javascript">).
- Without type="text/babel", JSX syntax will NOT work and the page will be blank.
- Use React state-based routing (NO BrowserRouter, NO React Router DOM — use hash-based or state)

APP ARCHITECTURE:
- Multi-page SPA using React state (currentPage / setCurrentPage) for routing
- Sidebar or top navbar with navigation links
- CRITICAL: For navigation links, use <button> OR if using <a href="#">, you MUST call e.preventDefault() in the onClick handler. Otherwise the host platform will reload!
- Build the pages and components necessary for the user's requested application.
- Use React.useState, React.useEffect, React.useCallback, React.useMemo (destructure from React)
- CRITICAL: Do NOT use `fetch()` or `axios` to make real HTTP requests to the backend (e.g., no calls to http://localhost:8000). The backend is not yet active.
- Instead, you MUST perfectly simulate API interactions by creating async functions that return realistic hardcoded mock data after a short `setTimeout` delay.
- Show loading spinners during these simulated API fetches.

DESIGN REQUIREMENTS (premium dark app):
- Background: #0a0c12 (near-black), card backgrounds: #0d1117 or #111827
- Accent: indigo-600 (#6366f1) with violet/purple gradients
- Glassmorphism cards: backdrop-filter blur, rgba borders
- Smooth hover effects on all interactive elements
- Sidebar with logo, nav items with icons, active state highlighting
- Top header bar with user avatar, breadcrumbs
- Rich data tables or card grids with badges, status pills, avatars
- Charts or stats panels using pure CSS/HTML (no chart library needed)

LAYOUT: Structure the layout exactly as needed for the user's requested application.

CRITICAL DESIGN RULE — DARK MODE ONLY:
- You MUST ALWAYS generate your app in DARK MODE. No exceptions.
- The <body> and root container background MUST be a dark color (e.g., #0a0c12, #0f172a, #111827).
- ALL text must use light/white colors (e.g., #e2e8f0, #f1f5f9, white) for maximum readability.
- Cards, sidebars, and panels should use slightly lighter dark shades (e.g., #1e293b, #1a1a2e).
- NEVER use a white or light background. NEVER use dark text on dark backgrounds.
- Ensure sufficient contrast between text and background at all times.

CRITICAL OUTPUT RULES:
- Your response MUST begin with <!DOCTYPE html> as the VERY FIRST characters.
- Do NOT include ANY text before <!DOCTYPE html>. No planning. No scratchpad. No thinking. No explanations.
- Do NOT use markdown code fences (no ```html or ```).
- Do NOT write "Here is", "Let me", "I'll create", or ANY preamble text.
- Do NOT add comments explaining what you are doing.
- ONLY output the raw, valid HTML5 document from <!DOCTYPE html> to </html>.
- The main app script MUST use <script type="text/babel"> so JSX is transpiled by Babel.
- CRITICAL: NEVER call React hooks (useState, useCallback, useMemo) at the top module level. All hooks MUST be inside a React function component body to avoid "Invalid hook call" errors.
- End with: const root = ReactDOM.createRoot(document.getElementById('root')); root.render(<App />);
- The entire app must work when pasted into a browser as an HTML file."""


# ─── Gemini streaming (primary) ───────────────────────────────────────────────

async def _gemini_stream(system: str, user: str) -> AsyncGenerator[str, None]:
    if not is_gemini_configured() or not client:
        raise Exception("Gemini API key not configured")

    try:
        print("[gemini_service] Starting stream...")
        # Async stream using new google-genai SDK
        response_stream = await client.aio.models.generate_content_stream(
            model='gemini-2.5-flash',
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.7,
                max_output_tokens=65536,
            )
        )
    except Exception as e:
        print(f"[gemini_service] Initial Error: {e}")
        raise e
        
    try:
        
        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text
            
            # Log finish reason and token usage if present
            try:
                if chunk.candidates and chunk.candidates[0].finish_reason:
                    reason = chunk.candidates[0].finish_reason
                    if reason != "STOP":
                        print(f"[gemini_service] WARNING: Stream stopped early! Reason: {reason}")
                    else:
                        print(f"[gemini_service] Stream completed normally. Reason: {reason}")
            except Exception:
                pass
                
            try:
                if chunk.usage_metadata:
                    print(f"[gemini_service] Usage metadata: {chunk.usage_metadata}")
            except Exception:
                pass

    except asyncio.TimeoutError:
        print("[gemini_service] Error: Request timed out")
        yield "<!-- Error: Timeout -->"
    except Exception as e:
        print(f"[gemini_service] Error: {e}")
        yield f"<!-- Error: {e} -->"


# ─── Public generators ────────────────────────────────────────────────────────

async def stream_website_gemini(prompt: str) -> AsyncGenerator[str, None]:
    user_msg = (
        f"Build a premium, high-quality UI for: {prompt}. "
        "Ensure it precisely matches the requested layout and functionality. Output ONLY raw HTML."
    )
    async for chunk in _gemini_stream(WEBSITE_SYSTEM, user_msg):
        yield chunk


async def stream_refine_gemini(current_code: str, prompt: str) -> AsyncGenerator[str, None]:
    user_msg = f"EXISTING HTML:\n{current_code}\n\nUSER REQUEST:\n{prompt}"
    async for chunk in _gemini_stream(REFINE_SYSTEM, user_msg):
        yield chunk


async def stream_fullstack_frontend_gemini(prompt: str) -> AsyncGenerator[str, None]:
    """Stream a complete self-contained React app HTML file via Gemini."""
    user_msg = (
        f"Build a complete, production-grade web application frontend for: {prompt}. "
        "Make it feel extremely premium and polished. "
        "Include realistic mock data. "
        "IMPORTANT: Start your response IMMEDIATELY with <!DOCTYPE html>. "
        "Do NOT include any text, planning, scratchpad, or explanation before the HTML. "
        "You MUST include Babel Standalone script and use <script type=\"text/babel\"> for your React/JSX code. "
        "Output ONLY the raw HTML file."
    )
    # Track whether we've found the HTML start yet
    preamble_done = False
    buffer = ''

    async for chunk in _gemini_stream(FULLSTACK_FRONTEND_SYSTEM, user_msg):
        if preamble_done:
            yield chunk
        else:
            buffer += chunk
            # Check if we've reached actual HTML content
            match = re.search(r'(?i)(<!doctype\s+html|<html|<!)', buffer)
            if match:
                preamble_done = True
                # Yield from the HTML start onward
                yield buffer[match.start():]
            # If buffer is getting large without finding HTML, flush it
            elif len(buffer) > 500:
                preamble_done = True
                yield buffer


def is_gemini_configured() -> bool:
    return bool(
        settings.GEMINI_API_KEY
        and not settings.GEMINI_API_KEY.startswith("your-")
    )
