"""Reads a hand-drawn sketch with Claude (Restruct Warp's main engine).

Sketch2UI's own reader (vision_ai) needs an OpenAI-compatible vision model, and its detector
needs trained YOLO weights plus heavy vision packages. Claude can read the whole sketch by
itself, so Sketch Studio works on a plain install; when the detector is present, its screens
and arrows are kept and Claude fills in what is inside each screen.
"""
import base64
import logging
from typing import Optional

from app.schemas.component_schema import UIDocument
from app.services import anthropic_service, llm_service, vision_ai

log = logging.getLogger(__name__)

MAX_TOKENS = 8000

# Added to Sketch2UI's prompt: without the detector, Claude also reports the drawn arrows (F2)
ARROWS = """
If arrows are drawn from an element on one screen to another screen, also add "l":[[FROM,"text of the button the arrow starts at",TO],...]
to the same JSON object, where FROM and TO are screen numbers counted from 1 in the order of "s". No arrows: leave "l" out."""


def blank_document(name: str) -> UIDocument:
    """Stand-in for the detector's result when no detector is installed: one empty screen."""
    full = {"x": 0, "y": 0, "w": 1, "h": 1}
    return UIDocument.model_validate({
        "name": name,
        "screens": [{"id": "screen_1", "name": "Screen 1",
                     "root": {"id": "screen_1_root", "type": "container", "layout": "column",
                              "bbox": full, "props": {}}}],
    })


async def describe(image: bytes, media_type: str, detected: UIDocument) -> Optional[UIDocument]:
    """Sketch photo -> UIDocument, or None if Claude is not configured or the reply can't be used."""
    if not anthropic_service.is_anthropic_configured():
        return None
    try:
        text = await anthropic_service.complete([{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                         "data": base64.standard_b64encode(image).decode()}},
            {"type": "text", "text": vision_ai.PROMPT + ARROWS},
        ]}], max_tokens=MAX_TOKENS)
        reply = llm_service.extract_json(text)
    except Exception as e:  # network, rate limit, refusal, bad JSON: the caller falls back
        log.warning("Claude could not read the sketch: %s", str(e)[:200])
        return None
    doc = vision_ai.to_document(reply, detected)
    if doc is None:
        log.warning("Claude's reply didn't fit the schema: %s", str(reply)[:300])
        return None
    if not doc.links:  # no detector arrows to keep: use the ones Claude saw
        doc = _with_links(doc, reply.get("l"))
    return doc


def _with_links(doc: UIDocument, arrows) -> UIDocument:
    """Adds Claude's arrows ([from screen, "button text", to screen], 1-based) as links, skipping bad ones."""
    links = []
    for arrow in arrows if isinstance(arrows, list) else []:
        try:
            src, words, dst = doc.screens[int(arrow[0]) - 1], str(arrow[1]).strip().lower(), doc.screens[int(arrow[2]) - 1]
        except (IndexError, TypeError, ValueError):
            continue
        if int(arrow[0]) < 1 or int(arrow[2]) < 1 or src is dst:
            continue
        clickable = [c for c in src.root.walk() if c.type in ("button", "iconbutton", "link")]
        start = next((c for c in clickable if words and (c.props.text or "").strip().lower() == words), None)
        start = start or next((c for c in clickable if c.type == "button"), None)
        if start and not any(l["fromComponent"] == start.id for l in links):
            links.append({"fromScreen": src.id, "fromComponent": start.id, "toScreen": dst.id})
    if not links:
        return doc
    try:
        return UIDocument.model_validate({**doc.model_dump(exclude_none=True), "links": links})
    except ValueError:
        return doc
