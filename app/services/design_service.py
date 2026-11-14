"""Turns the plain template pages into a designed site with Claude.

codegen_service renders every sketch through one fixed template, which is correct but generic.
Here Claude sees the sketch photo, the component tree and those template pages, and writes the
real pages: same elements, same links, proper visual design. Any failure -> None, and the
caller keeps the template pages.
"""
import base64
import logging
import re
from typing import Optional

from app.schemas.component_schema import UIDocument
from app.services import anthropic_service

log = logging.getLogger(__name__)

MAX_TOKENS = 64000
MARK = "=====FILE: {} ====="
SPLIT = re.compile(r"^=====FILE: (.+?) =====\s*$", re.M)

SYSTEM = """You are a senior product designer and frontend engineer. A user drew an app or website on paper.
It was read into a component tree and rendered through a generic template. Design the real thing.

You get: the photo of the sketch (when available), the component tree as JSON, and the template pages.

Design:
- Decide what product this is from the sketch and give it a fitting, distinctive visual identity:
  a considered colour palette, type scale, spacing rhythm, depth and hover/focus states. It should
  look like a shipped product, not a wireframe or a template.
- Follow the layout the user drew: what is side by side, stacked, at the top or at the bottom, and how
  large things are relative to each other. If the sketch is a phone screen, design a mobile app screen
  (centred in a phone-width column on wide viewports); if it is a wide page, design a full-width
  responsive web page.
- Keep EVERY element from the component tree, in the same order and with the same purpose. You may add
  small supporting details a real product would have (icons, helper text, dividers), but never drop,
  merge or replace what was drawn.
- Replace empty or placeholder labels with short realistic copy that fits the product. Keep text the
  user actually wrote.
- Images: never link external image files. Use inline SVG illustrations/icons or CSS gradients sized
  like the drawn image, with a meaningful alt or aria-label.
- All pages of one site share the same identity, navigation and components.

Technical rules:
- Each page is one complete, self-contained HTML document. Tailwind via
  <script src="https://cdn.tailwindcss.com"></script> and Google Fonts <link> tags are allowed;
  no other external files. A little inline <script> for interactions (tabs, toggles, toasts) is fine.
- Navigation between pages: wherever the template page links to another page (an <a href="x.html">, or a
  button with data-next="x.html"), your page must have a plain <a href="x.html"> to the same file on the
  matching element, styled as that element (e.g. as the primary button). Never navigate with JavaScript.
  Use exactly the file names given; do not invent pages.
- Keep form fields' name and type attributes from the template pages.
- Accessible: <html lang>, <title>, one <main>, a label or aria-label for every input, alt text,
  visible focus styles, sufficient colour contrast.

Output format: for every page, a line `=====FILE: name.html =====` followed by that page's full HTML,
starting with <!DOCTYPE html>. Output every page you were given, nothing else: no markdown fences, no commentary."""


def _parse(reply: str, names: list[str]) -> Optional[dict[str, str]]:
    parts = SPLIT.split(reply)
    pages = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        html = re.sub(r"^\s*```(?:html)?\s*|\s*```\s*$", "", body.strip())
        start = re.search(r"<!doctype html", html, re.I)
        if start and "</html>" in html.lower():
            pages[name.strip()] = html[start.start():html.lower().rindex("</html>") + 7] + "\n"
    return {n: pages[n] for n in names} if all(n in pages for n in names) else None


async def design_site(doc: UIDocument, pages: dict[str, str], image: Optional[bytes] = None,
                      media_type: str = "image/png") -> Optional[dict[str, str]]:
    """{file: designed html} for the same files as `pages`, or None if Claude can't be used."""
    if not anthropic_service.is_anthropic_configured():
        return None
    content = []
    if image:
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                    "data": base64.standard_b64encode(image).decode()}})
    template = "\n\n".join(f"{MARK.format(name)}\n{html}" for name, html in pages.items())
    content.append({"type": "text", "text": (
        f"Site name: {doc.name}\nPages: {', '.join(pages)}\n\n"
        f"COMPONENT TREE (JSON):\n{doc.model_dump_json(exclude_none=True)}\n\n"
        f"TEMPLATE PAGES:\n{template}"
    )})
    try:
        reply = await anthropic_service.complete([{"role": "user", "content": content}], system=SYSTEM,
                                                 max_tokens=MAX_TOKENS, effort="medium")
    except Exception as e:  # network, rate limit, refusal: the template pages stand
        log.warning("Claude could not design the pages: %s", str(e)[:200])
        return None
    designed = _parse(reply, list(pages))
    if designed is None:
        log.warning("Claude's design reply was missing pages; keeping the template pages")
    return designed
