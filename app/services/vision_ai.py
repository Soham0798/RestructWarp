"""Read the sketch with the vision model, so elements the detector has no class for
(icons, tabs, maps, charts, timelines...) still make it into the page.

The detector still finds the screens and the arrows; this replaces what's inside each screen.
Groq's free tier lets the vision model write ~1000 tokens a minute, so it answers in a compact
array format (below) that this module expands into a UIDocument. Any failure -> None, and the
caller keeps the detector's document.
"""
import base64
import logging
import re
from itertools import count
from typing import Optional

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.schemas.component_schema import UIDocument
from app.services import icons, llm_service

MAX_TOKENS = 950
log = logging.getLogger(__name__)

PROMPT = """Read this hand-drawn app wireframe. Reply with ONLY compact JSON, no spaces:
{"s":[["Screen name",[NODE,...]],...]}  one entry per drawn phone/frame/screen, left to right.
NODE = ["type"] or ["type","text"] or ["type","text",[NODE,...]] (children)
types: nav,h,t,btn,ibtn,icon,input,search,img,carousel,card,row,col,list,tabs,bnav,map,progress,timeline,chart,table,rating,price,badge,check,toggle,slider,select,link,footer
ibtn/icon text = icon name: back,menu,search,bell,heart,location,home,cart,bag,user,star,plus,arrow,phone,chat,truck,filter,settings,share,close,check,chevron
tabs/bnav/timeline/table text = labels joined by "|". chart text = "pie|label|label..." (first part: pie, donut, bar or line).
progress/rating text = a number. carousel = a big image with dots under it.
Keep EVERY drawn element, in reading order; things side by side go in a row; a list item is a row inside a list.
Squiggles are placeholder text: write short realistic text that fits this app. Use h for screen titles and section titles."""

TYPES = {
    "nav": "navbar", "h": "heading", "t": "text", "btn": "button", "ibtn": "iconbutton", "icon": "icon",
    "input": "input", "search": "search", "img": "image", "carousel": "carousel", "card": "card",
    "row": "container", "col": "container", "list": "list", "item": "listitem", "tabs": "tabs",
    "bnav": "bottomnav", "map": "map", "progress": "progress", "timeline": "timeline", "chart": "chart",
    "table": "table", "rating": "rating", "price": "price", "badge": "badge", "check": "checkbox",
    "toggle": "toggle", "slider": "slider", "select": "dropdown", "link": "link", "footer": "footer",
}
BOXES = {"navbar", "card", "container", "footer", "list", "listitem"}
LISTED = {"tabs", "bottomnav", "timeline", "table", "chart", "dropdown"}
SEE_ALL = re.compile(r"^(see|view) (all|more)$|^more$", re.I)


def _split(rest: list) -> tuple[str, list]:
    """(text, child nodes) from what follows a node's type. The model writes children either
    wrapped (["row","",[[..],[..]]]) or inline (["row",[..],[..]]); both are accepted."""
    text, kids = None, []
    for x in rest:
        if isinstance(x, (str, int, float)) and not isinstance(x, bool) and text is None:
            text = str(x)
        elif isinstance(x, list) and x:
            kids.extend(x) if isinstance(x[0], list) else kids.append(x)
    return text or "", kids


def _num(text: str) -> Optional[float]:
    m = re.search(r"\d+(\.\d+)?", text or "")
    return float(m.group()) if m else None


class _Builder:
    """Expands compact nodes into schema dicts, giving each a unique id and a stacked bbox."""

    def __init__(self, prefix: str):
        self.prefix, self.n = prefix, count(1)

    def node(self, raw, box) -> Optional[dict]:
        if not isinstance(raw, list) or not raw or not isinstance(raw[0], str):
            return None
        code = raw[0].strip().lower()
        kind = TYPES.get(code)
        if not kind:
            return None
        text, kids = _split(raw[1:])
        c = {"id": f"{self.prefix}_{next(self.n)}", "type": kind, "bbox": box, "props": {}}
        p = c["props"]
        if kind in ("icon", "iconbutton"):
            p["icon"] = icons.name_of(text)
            p["ariaLabel"] = p["icon"].replace("back", "Go back")
        elif kind in LISTED:
            parts = [s.strip() for s in text.split("|") if s.strip()]
            if kind == "chart":
                p["variant"] = (parts.pop(0).lower() if parts and parts[0].lower() in ("pie", "donut", "bar", "line") else "bar")
            p["options"] = parts or None
            if kind == "dropdown":
                p["ariaLabel"] = parts[0] if parts else "Choose"
        elif kind in ("progress", "rating"):
            p["value"] = _num(text) or (60 if kind == "progress" else 4.5)
        elif kind == "image" or kind == "carousel":
            p["alt"] = text
        elif kind in ("input", "search", "textarea"):
            p["placeholder"] = text or ("Search" if kind == "search" else None)
            p["ariaLabel"] = text or kind.title()
        elif kind == "heading":
            p["text"], p["level"] = text, 2
        elif kind == "slider":
            p["ariaLabel"], p["value"] = text or "Value", 50
        elif text:
            p["text"] = text
        if code in ("row", "col"):
            c["layout"] = "row" if code == "row" else "column"
        if kind in BOXES:
            children = [self.node(k, self._child(box, i, len(kids), code == "row")) for i, k in enumerate(kids)]
            c["children"] = [k for k in children if k]
            c.setdefault("layout", "row" if kind in ("navbar", "listitem") else "column")
        c["props"] = {k: v for k, v in p.items() if v not in (None, "")}
        return c

    @staticmethod
    def _child(box, i, n, across) -> dict:
        n = max(n, 1)
        if across:
            w = box["w"] / n
            return {"x": round(box["x"] + i * w, 4), "y": box["y"], "w": round(w, 4), "h": box["h"]}
        h = box["h"] / n
        return {"x": box["x"], "y": round(box["y"] + i * h, 4), "w": box["w"], "h": round(h, 4)}


PRICE = re.compile(r"^\s*[₹$€£¥]\s?\d")
STATIC_ICONS = {"truck", "location", "star", "check"}  # pictures, not things to press


def _tidy(c: dict, parent: Optional[dict] = None) -> dict:
    """Small fixes that make the page read like the sketch (the model's answers vary; these don't)."""
    kids = c.get("children", [])
    for k in kids:
        _tidy(k, c)
        # a box with just an X in it is the wireframe sign for a picture
        inner = k.get("children", [])
        if k["type"] in ("card", "container") and len(inner) == 1 and inner[0]["props"].get("icon") == "close":
            k.update({"type": "image", "props": {"alt": ""}})
            k.pop("children"), k.pop("layout", None)
        if k["type"] == "text" and PRICE.match(k["props"].get("text", "")):
            k["type"] = "price"
        if k["type"] == "iconbutton" and k["props"].get("icon") in STATIC_ICONS:
            k["type"] = "icon"
    # a star next to a number is a rating
    for i in range(len(kids) - 1):
        a, b = kids[i], kids[i + 1]
        if not (a and b and b["type"] == "text"):
            continue
        words = b["props"].get("text", "")
        star = a["type"] == "icon" and a["props"].get("icon") == "star"
        if (star or a["type"] == "rating") and re.match(r"^\s*\d", words):
            # "4.5 (120 reviews)": the number joins the rating, the rest stays as text
            rest = re.sub(r"^\s*\d+(\.\d+)?\s*", "", words)
            kids[i] = {"id": a["id"], "type": "rating", "bbox": a["bbox"], "props": {"value": _num(words)}}
            if rest:
                b["props"]["text"] = rest
            else:
                kids[i + 1] = None
    c["children"] = kids = [k for k in kids if k]
    types = [k["type"] for k in kids]
    if c.get("layout") == "row":
        # rows of only pictures standing next to each other are one picture grid (a drawn 2x2)
        grid = [k for k in kids if k.get("layout") == "row" and k.get("children") and {g["type"] for g in k["children"]} == {"image"}]
        if len(grid) >= 2:
            first = kids.index(grid[0])
            box = {"id": grid[0]["id"] + "_grid", "type": "container", "layout": "column", "bbox": grid[0]["bbox"],
                   "props": {}, "children": grid}
            kids = [k for k in kids if k not in grid]
            kids.insert(first, box)
            c["children"] = kids
            types = [k["type"] for k in kids]
        # a strip of 3+ pictures is a row of category tiles (caption = what the model called them)
        if len(kids) >= 3 and set(types) == {"image"}:
            for k in kids:
                cap = {"id": k["id"] + "_cap", "type": "text", "bbox": k["bbox"], "props": {"text": k["props"].get("alt") or ""}}
                k.update({"type": "container", "layout": "column", "props": {}, "children": [
                    {"id": k["id"] + "_img", "type": "image", "bbox": k["bbox"], "props": {"alt": ""}}, cap]})
            types = [k["type"] for k in kids]
        # 3+ short words side by side are tabs
        if len(kids) >= 3 and set(types) == {"text"} and all(len(k["props"].get("text", "").split()) <= 2 for k in kids):
            c.clear()
            c.update({"id": kids[0]["id"] + "_tabs", "type": "tabs", "bbox": kids[0]["bbox"],
                      "props": {"options": [k["props"]["text"] for k in kids]}})
            return c
        # side-by-side [icon + words] pairs are buttons ("Call", "Chat")
        if len(kids) >= 2 and all(k["type"] == "container" and [g["type"] for g in k.get("children", [])][-1:] == ["text"]
                                  and {g["type"] for g in k["children"][:-1]} <= {"icon", "iconbutton"} for k in kids):
            for k in kids:
                icon = next((g["props"].get("icon") for g in k["children"] if g["type"] in ("icon", "iconbutton")), None)
                k.update({"type": "button", "props": {"text": k["children"][-1]["props"]["text"], **({"icon": icon} if icon else {})}})
                k.pop("children"), k.pop("layout", None)
            types = [k["type"] for k in kids]
    # a row of image+caption pairs is a strip of category tiles
    if c.get("layout") == "row" and len(kids) >= 4 and types[0::2] == ["image"] * len(types[0::2]) \
            and set(types[1::2]) <= {"text"} and len(kids) % 2 == 0:
        c["children"] = [{"id": f'{a["id"]}_tile', "type": "container", "layout": "column", "bbox": a["bbox"],
                          "props": {}, "children": [a, b]} for a, b in zip(kids[0::2], kids[1::2])]
    # "Popular" ... "See all": section title + link
    if c.get("layout") == "row" and len(kids) == 2 and types == ["text", "text"] \
            and SEE_ALL.match(kids[1]["props"].get("text", "").strip()):
        kids[0]["type"], kids[0]["props"]["level"] = "heading", 3
        kids[1]["type"] = "link"
    # back arrow + words: the words are the screen title
    if c.get("layout") == "row" and "iconbutton" in types and kids and kids[0]["props"].get("icon") == "back":
        for k in kids:
            if k["type"] == "text":
                k["type"], k["props"]["level"] = "heading", 3
                break
    # a bar of [icon] text [arrow] is one big button (e.g. "Add to cart ->")
    if c.get("layout") == "row" and set(types) <= {"iconbutton", "icon", "text"} and "text" in types \
            and any(k["props"].get("icon") == "arrow" for k in kids) and parent is not None:
        label = next(k["props"]["text"] for k in kids if k["type"] == "text")
        lead = next((k["props"]["icon"] for k in kids if k["type"] in ("icon", "iconbutton") and k["props"].get("icon") != "arrow"), None)
        c.clear()
        c.update({"id": kids[0]["id"] + "_bar", "type": "button", "bbox": kids[0]["bbox"],
                  "props": {"text": label, **({"icon": lead} if lead else {})}})
    # rows inside a list are list items
    if c.get("type") == "list":
        for k in c["children"]:
            if k["type"] == "container" and k.get("layout") == "row":
                k["type"] = "listitem"
    return c


def _sync_progress(root: dict) -> None:
    """A timeline on the same screen as a progress bar is at the step the bar shows."""
    def walk(c):
        yield c
        for k in c.get("children", []):
            yield from walk(k)

    nodes = list(walk(root))
    bar = next((c for c in nodes if c["type"] == "progress"), None)
    for line in (c for c in nodes if c["type"] == "timeline" and "value" not in c["props"]):
        steps = len(line["props"].get("options") or []) or 4
        if bar:
            line["props"]["value"] = round(bar["props"].get("value", 60) / 100 * (steps - 1))


def to_document(reply: dict, detected: UIDocument) -> Optional[UIDocument]:
    """Compact reply + the detector's document (screens, arrows) -> validated UIDocument."""
    screens_in = reply.get("s") if isinstance(reply, dict) else None
    if not isinstance(screens_in, list) or not screens_in:
        return None
    same = len(screens_in) == len(detected.screens)
    screens = []
    for i, entry in enumerate(screens_in):
        if not (isinstance(entry, list) and len(entry) >= 2 and isinstance(entry[0], str)):
            return None
        _, nodes = _split(entry[1:])
        if not nodes:
            return None
        sid = detected.screens[i].id if same else f"screen_{i + 1}"
        name = entry[0].strip() or (detected.screens[i].name if same else f"Screen {i + 1}")
        b = _Builder(sid)
        full = {"x": 0, "y": 0, "w": 1, "h": 1}
        kids = [b.node(k, _Builder._child(full, j, len(nodes), False)) for j, k in enumerate(nodes)]
        root = {"id": f"{sid}_root", "type": "container", "layout": "column", "bbox": full, "props": {},
                "children": [k for k in kids if k]}
        _sync_progress(_tidy(root))
        first = root["children"][0] if root["children"] else None
        if first and first["type"] == "text":  # words alone at the top are the page title
            first["type"], first["props"]["level"] = "heading", 1
        screens.append({"id": sid, "name": name, "root": root})
    doc = {"name": detected.name, "screens": screens, "links": _links(detected, screens) if same else []}
    try:
        return UIDocument.model_validate(doc)
    except ValidationError:
        return None


def _links(detected: UIDocument, screens: list[dict]) -> list[dict]:
    """Keep the drawn arrows: start each at the button with the same words, else the first button."""
    def walk(c):
        yield c
        for k in c.get("children", []):
            yield from walk(k)

    out = []
    for link in detected.links:
        start = next(c for s in detected.screens if s.id == link.fromScreen for c in s.root.walk() if c.id == link.fromComponent)
        words = (start.props.text or "").strip().lower()
        screen = next(s for s in screens if s["id"] == link.fromScreen)
        clickable = [c for c in walk(screen["root"]) if c["type"] in ("button", "iconbutton", "link")]
        match = next((c for c in clickable if words and c["props"].get("text", "").strip().lower() == words), None)
        match = match or next((c for c in clickable if c["type"] == "button"), None)
        if match:
            out.append({"fromScreen": link.fromScreen, "fromComponent": match["id"], "toScreen": link.toScreen})
    return out


async def describe(image: bytes, detected: UIDocument, client: Optional[AsyncOpenAI] = None) -> Optional[UIDocument]:
    if client is None and not (llm_service.is_configured() and settings.LLM_VISION_MODEL):
        return None
    client = client or llm_service.make_client()
    url = "data:image/jpeg;base64," + base64.b64encode(image).decode()
    try:
        res = await client.chat.completions.create(
            model=settings.LLM_VISION_MODEL, temperature=0.2, max_tokens=MAX_TOKENS,
            extra_body={"reasoning_effort": "none"},  # qwen3 would spend the token budget thinking
            messages=[{"role": "user", "content": [{"type": "text", "text": PROMPT},
                                                   {"type": "image_url", "image_url": {"url": url}}]}])
        reply = llm_service.extract_json(res.choices[0].message.content or "")
    except Exception as e:  # rate limit, network, bad JSON: the detector's document stands
        log.warning("vision model unavailable, keeping the detector's result: %s", str(e)[:200])
        return None
    doc = to_document(reply, detected)
    if doc is None:
        log.warning("vision reply didn't fit the schema, keeping the detector's result: %s", str(reply)[:300])
    return doc
