"""Step 19: read handwritten text once for the whole sketch, then hand each line to its box.

One OCR pass over the page is much faster than one per box, and it also catches labels
written beside a box (a checkbox's caption) rather than inside it.
"""
from functools import lru_cache

import cv2
import numpy as np

from app.config import settings
from app.services.vision.types import Detection

TEXT_BEARING = ("heading", "text", "button", "input", "textarea", "dropdown", "note", "card", "checkbox")
MIN_SCORE = 0.5


class OCRUnavailable(RuntimeError):
    """PaddleOCR is not installed, or it crashed on this machine."""


@lru_cache(maxsize=1)
def _engine():
    try:
        from paddleocr import PaddleOCR
    except ImportError as e:
        raise OCRUnavailable("pip install -r requirements-vision.txt") from e
    try:  # PaddleOCR 3.x
        return PaddleOCR(lang="en", use_doc_orientation_classify=False, use_doc_unwarping=False,
                         use_textline_orientation=False,
                         text_detection_model_name=f"{settings.OCR_MODEL}_det",
                         text_recognition_model_name=f"{settings.OCR_MODEL}_rec",
                         **({"engine": "onnxruntime"} if settings.OCR_ENGINE == "onnxruntime"
                            else {"enable_mkldnn": False}))  # Paddle 3.3's oneDNN path crashes on Windows CPUs
    except TypeError:  # PaddleOCR 2.x
        return PaddleOCR(lang="en", use_angle_cls=False, show_log=False)


def for_ocr(img: np.ndarray) -> np.ndarray:
    """Stretch grey ink to black: after shadow removal a blurry photo's ink is too faint to be found."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lo, hi = np.percentile(gray, 1), np.percentile(gray, 99)
    gray = np.clip((gray - lo) * 255.0 / max(1.0, hi - lo), 0, 255).astype(np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def read_lines(img: np.ndarray) -> list[tuple[str, float, tuple[float, float, float, float]]]:
    """[(text, score, (x1, y1, x2, y2)), ...] for every line of text in the image."""
    engine = _engine()
    lines = []
    if hasattr(engine, "predict"):  # 3.x
        for res in engine.predict(img):
            r = res.json.get("res", res.json) if hasattr(res, "json") else res
            for text, score, poly in zip(r["rec_texts"], r["rec_scores"], r["rec_polys"]):
                xs, ys = [p[0] for p in poly], [p[1] for p in poly]
                lines.append((text, float(score), (min(xs), min(ys), max(xs), max(ys))))
    else:  # 2.x
        for poly, (text, score) in (engine.ocr(img, cls=False)[0] or []):
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            lines.append((text, float(score), (min(xs), min(ys), max(xs), max(ys))))
    return [l for l in lines if l[1] >= MIN_SCORE and l[0].strip()]


def _holder(holders: list[Detection], x1: float, x2: float, cx: float, cy: float) -> Detection | None:
    """The smallest text-bearing box holding (cx, cy), or a checkbox whose caption starts at x1."""
    inside = [d for d in holders if d.x1 <= cx <= d.x2 and d.y1 <= cy <= d.y2]
    if not inside:  # caption to the right of a checkbox, on the same row
        inside = [d for d in holders if d.cls == "checkbox" and d.y1 - 10 <= cy <= d.y2 + 10
                  and 0 <= x1 - d.x2 <= 3 * (d.x2 - d.x1) + 20]
    return min(inside, key=lambda d: d.area) if inside else None


def _words(text: str, x1: float, x2: float):
    """Split a line into words with their x span, assuming evenly wide characters."""
    per_char = (x2 - x1) / max(1, len(text))
    start = 0
    for word in text.split():
        start = text.index(word, start)
        yield word, x1 + start * per_char, x1 + (start + len(word)) * per_char
        start += len(word)


def assign_text(dets: list[Detection], lines) -> None:
    """Put each OCR word into the smallest text-bearing box holding it (or beside a checkbox).

    Word by word, because OCR joins a label and the note written just after it into one line
    ("Sign up green"): the button should get "Sign up" and the note "green".
    """
    holders = [d for d in dets if d.cls in TEXT_BEARING]
    for text, _, (x1, y1, x2, y2) in sorted(lines, key=lambda l: (l[2][1], l[2][0])):
        if len(text.strip()) == 1 and not text.isascii():
            continue  # an empty square read as a CJK glyph (口, 区), not a real label
        cy = (y1 + y2) / 2
        whole = _holder(holders, x1, x2, (x1 + x2) / 2, cy)
        groups: list[tuple[Detection, list[str]]] = []
        for word, wx1, wx2 in _words(text, x1, x2):
            target = _holder(holders, wx1, wx2, (wx1 + wx2) / 2, cy) or whole
            if target is None:
                continue
            if groups and groups[-1][0] is target:
                groups[-1][1].append(word)
            else:
                groups.append((target, [word]))
        for target, words in groups:
            target.text = f"{target.text} {' '.join(words)}".strip()


def read_text(img: np.ndarray, dets: list[Detection]) -> list[Detection]:
    try:
        lines = read_lines(for_ocr(img))
    except OCRUnavailable:
        raise
    except Exception as e:  # a broken OCR install shouldn't fail the whole sketch
        raise OCRUnavailable(f"OCR failed: {e}") from e
    assign_text(dets, lines)
    return dets
