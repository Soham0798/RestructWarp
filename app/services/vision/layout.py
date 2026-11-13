"""Turn detected boxes into a UIDocument: screens, nesting, rows/columns, props (Step 20)."""
import re
from collections import Counter

from app.schemas.component_schema import CONTAINER_TYPES, UIDocument
from app.services.vision import flow, notes
from app.services.vision.types import Detection

SCREEN_MIN_SHARE = 0.12  # an outer container covering this much of the image is a screen


def find_screens(dets: list[Detection], img_w: int, img_h: int) -> list[Detection]:
    big = [d for d in dets if d.cls == "container" and d.area >= SCREEN_MIN_SHARE * img_w * img_h]
    outer = [d for d in big if not any(o is not d and o.contains(d) for o in big)]
    if not outer:  # no frame drawn: the whole photo is one screen
        return [Detection("container", 0, 0, img_w, img_h)]
    return sorted(outer, key=lambda d: (d.x1, d.y1))  # left to right, as people draw flows


def _frac(d: Detection, screen: Detection) -> dict:
    sw, sh = screen.x2 - screen.x1, screen.y2 - screen.y1
    clamp = lambda v: round(min(1.0, max(0.0, v)), 4)
    x, y = clamp((d.x1 - screen.x1) / sw), clamp((d.y1 - screen.y1) / sh)
    return {"x": x, "y": y, "w": max(clamp((d.x2 - d.x1) / sw), 0.0001), "h": max(clamp((d.y2 - d.y1) / sh), 0.0001)}


def _layout(children: list[Detection]) -> str:
    """'row' when most neighbours sit side by side, else 'column'."""
    if len(children) < 2:
        return "column"
    side_by_side = sum(1 for a, b in zip(children, children[1:])
                       if min(a.y2, b.y2) - max(a.y1, b.y1) > 0.5 * min(a.y2 - a.y1, b.y2 - b.y1))
    return "row" if side_by_side >= (len(children) - 1) / 2 else "column"


def _reading_order(items: list[Detection]) -> list[Detection]:
    return sorted(items, key=lambda d: (round(d.y1 / 20), d.x1))  # rows of ~20px, then left to right


def _props(d: Detection, heading_rank: dict) -> dict:
    t = d.text.strip()
    if d.cls == "heading":
        return {"text": t or "Heading", "level": heading_rank.get(id(d), 2)}
    if d.cls in ("button", "text"):
        return {"text": t or d.cls.title()}
    if d.cls in ("input", "textarea"):
        return {"placeholder": t, "ariaLabel": t or d.cls.title()}
    if d.cls == "image":
        return {"alt": t or "Image"}
    if d.cls == "checkbox":
        return {"text": t, "checked": False}
    if d.cls == "dropdown":
        return {"options": [t] if t else [], "ariaLabel": t or "Select"}
    return {}


def _field_type(label: str) -> str:
    low = label.lower()
    for word, kind in (("mail", "email"), ("pass", "password"), ("phone", "number"), ("age", "number"), ("date", "date")):
        if word in low:
            return kind
    return "text"


def _slug(label: str, fallback: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return s if s and not s[0].isdigit() else fallback


def _infer_form(node: dict) -> None:
    """F4: a card/container holding inputs and a button is a form; describe its fields."""
    kids = node.get("children", [])
    inputs = [c for c in kids if c["type"] in ("input", "textarea", "checkbox", "dropdown")]
    if node["type"] in ("card", "container") and inputs and any(c["type"] == "button" for c in kids):
        kind = {"textarea": "textarea", "checkbox": "checkbox", "dropdown": "select"}
        fields, used = [], set()
        for i, c in enumerate(inputs, 1):
            label = c["props"].get("placeholder") or c["props"].get("text") or c["props"].get("ariaLabel") or ""
            name = _slug(label, f"field_{i}")
            while name in used:
                name += "_2"
            used.add(name)
            fields.append({"name": name, "label": label or None, "componentId": c["id"],
                           "type": kind.get(c["type"]) or _field_type(label), "required": c["type"] == "input"})
        node["form"] = {"name": _slug(node["props"].get("text", ""), f"{node['id']}_form"), "fields": fields}


def build_document(dets: list[Detection], img_w: int, img_h: int, name: str = "Sketch") -> UIDocument:
    screens = find_screens(dets, img_w, img_h)
    arrows = [d for d in dets if d.cls == "arrow"]
    note_dets = [d for d in dets if d.cls == "note"]
    elements = [d for d in dets if d.cls not in ("arrow", "note") and not any(d is s for s in screens)]

    counter: Counter = Counter()
    node_of: dict[int, dict] = {}       # id(detection) -> component dict
    screen_of: dict[int, str] = {}      # id(detection) -> screen id
    out_screens = []

    for si, screen in enumerate(screens, 1):
        sid = f"screen_{si}"
        mine = [d for d in elements if screen.contains(d)]
        headings = sorted((d for d in mine if d.cls == "heading"), key=lambda d: -(d.y2 - d.y1))
        heading_rank = {id(d): (1 if i == 0 else 2) for i, d in enumerate(headings)}

        def parent_of(d):
            holders = [p for p in mine if p is not d and p.cls in CONTAINER_TYPES and p.contains(d)]
            return min(holders, key=lambda p: p.area) if holders else None

        children: dict[int, list[Detection]] = {id(screen): []}
        for d in mine:
            children.setdefault(id(d), [])
        for d in mine:
            p = parent_of(d)
            children[id(p) if p else id(screen)].append(d)

        def make(d: Detection, root=False) -> dict:
            counter[d.cls] += 1
            node = {"id": f"{sid}_root" if root else f"{d.cls}_{counter[d.cls]}", "type": d.cls,
                    "bbox": _frac(d, screen), "props": {} if root else _props(d, heading_rank)}
            if d.conf < 1.0:
                node["confidence"] = round(d.conf, 3)
            kids = _reading_order(children.get(id(d), []))
            if d.cls in CONTAINER_TYPES:
                node["layout"] = _layout(kids)
                node["children"] = [make(k) for k in kids]
            node_of[id(d)] = node
            screen_of[id(d)] = sid
            _infer_form(node)
            return node

        root = make(screen, root=True)
        out_screens.append({"id": sid, "name": f"Screen {si}", "root": root})

    notes.attach(note_dets, [d for d in elements if id(d) in node_of], node_of)
    links = flow.link_arrows(arrows, screens, [d for d in elements if id(d) in node_of],
                             [s["id"] for s in out_screens], node_of, screen_of)
    return UIDocument.model_validate({"name": name, "screens": out_screens, "links": links})
