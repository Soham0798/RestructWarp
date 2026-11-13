"""F3: attach each handwritten note to the element it sits next to (Step 22)."""
from app.services.vision.types import Detection

MAX_GAP = 120  # px; a note further than this from every element is ignored


def nearest(note: Detection, elements: list[Detection]) -> Detection | None:
    """The element the note was written beside: same row first, then the smallest gap.

    Notes go to the right of an element, so the box below can be almost as close; a box whose
    height spans the note's middle wins over one that only happens to be near.
    """
    leaves = [e for e in elements if e.cls not in ("container",) and e is not note]
    cy = note.center[1]
    off_row = lambda e: not (e.y1 <= cy <= e.y2)
    best = min(leaves, key=lambda e: (note.distance_to(e) > MAX_GAP, off_row(e), note.distance_to(e), e.area),
               default=None)
    return best if best is not None and note.distance_to(best) <= MAX_GAP else None


def attach(note_dets: list[Detection], elements: list[Detection], node_of: dict[int, dict]) -> None:
    """Add each note's text to its element's styleHints.notes (the LLM turns it into styles later)."""
    for note in note_dets:
        word = note.text.strip()
        target = nearest(note, elements) if word else None
        if target is None:
            continue
        hints = node_of[id(target)].setdefault("styleHints", {"notes": [], "styles": {}})
        hints["notes"].append(word)
