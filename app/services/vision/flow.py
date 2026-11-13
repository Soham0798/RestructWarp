"""F2: turn drawn arrows into links between screens (Step 21).

An arrow's box stretches from the element it starts at to the screen it points to.
The start is the clickable element on one screen nearest the arrow's box; the target
is the other screen the arrow box reaches into or touches.
"""
from app.services.vision.types import Detection

CLICKABLE = ("button", "text", "image", "card", "heading")
NEAR = 40  # px


def _overlap(a: Detection, b: Detection) -> float:
    w = min(a.x2, b.x2) - max(a.x1, b.x1)
    h = min(a.y2, b.y2) - max(a.y1, b.y1)
    return max(0.0, w) * max(0.0, h)


def link_arrows(arrows, screens, elements, screen_ids, node_of, screen_of) -> list[dict]:
    links, seen = [], set()
    for arrow in arrows:
        starts = [e for e in elements if e.cls in CLICKABLE and arrow.distance_to(e) <= NEAR]
        if not starts:
            continue
        # prefer buttons, then whatever sits closest to the arrow's edge
        start = min(starts, key=lambda e: (e.cls != "button", arrow.distance_to(e), -_overlap(arrow, e)))
        from_screen = screen_of[id(start)]
        targets = [(sid, s) for sid, s in zip(screen_ids, screens) if sid != from_screen]
        targets = [(sid, s) for sid, s in targets if arrow.distance_to(s) <= NEAR]
        if not targets:
            continue
        to_screen = min(targets, key=lambda t: (arrow.distance_to(t[1]), -_overlap(arrow, t[1])))[0]
        key = (from_screen, node_of[id(start)]["id"], to_screen)
        if key not in seen:
            seen.add(key)
            links.append({"fromScreen": key[0], "fromComponent": key[1], "toScreen": key[2]})
    return links
