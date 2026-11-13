"""Step 42 baseline: give the same test sketches straight to a vision LLM (no YOLO, no OCR).

Answers "why not just ask ChatGPT?". Both systems are scored the same way, on what an LLM can
report without boxes: how many elements of each type the sketch has.

    python ml/baseline_vlm.py --limit 30 --json docs/results/baseline_vlm.json

Needs LLM_API_KEY and LLM_VISION_MODEL in .env (e.g. a Groq vision model).

Metrics (0-1, per type, credit up to the true count):
  count_recall      true elements the system accounted for
  count_precision   reported elements that really exist
  exact_sketches    sketches where every type's count is exactly right
"""
import argparse
import asyncio
import base64
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.services import llm_service  # noqa: E402
from app.services.vision import detect, preprocess  # noqa: E402

CLASSES = json.loads((ROOT / "shared" / "detector_classes.json").read_text())
PROMPT = ("List every UI element in this hand-drawn sketch. Reply with JSON only: "
          '{"elements": [{"type": "<one of ' + ", ".join(CLASSES) + '>"}]}. '
          "Count each screen frame as one 'container', each drawn arrow as 'arrow', each handwritten side note as 'note'.")


def gt_counts(label: Path) -> Counter:
    return Counter(CLASSES[int(l.split()[0])] for l in label.read_text().split("\n") if l.strip())


def encode(img: Path, max_side: int) -> str:
    """JPEG, shrunk so the free tier's tokens-per-minute budget isn't spent on pixels."""
    im = cv2.imread(str(img))
    scale = min(1.0, max_side / max(im.shape[:2]))
    im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else im
    return base64.b64encode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()).decode()


async def ask_llm(img: Path, max_side: int = 1024, tries: int = 4) -> Counter:
    b64 = encode(img, max_side)
    for attempt in range(tries):
        try:
            reply = await llm_service.chat([{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                model=settings.LLM_VISION_MODEL, json_mode=True)
            break
        except llm_service.LLMUnavailable as e:
            if "429" not in str(e) or attempt == tries - 1:
                raise
            await asyncio.sleep(20 * (attempt + 1))  # rate limited: wait for the per-minute budget to refill
    elements = llm_service.extract_json(reply).get("elements", [])
    return Counter(e.get("type") for e in elements if isinstance(e, dict))


def ours(img: Path) -> Counter:
    cleaned = preprocess.clean(cv2.imread(str(img)))
    return Counter(d.cls for d in detect.detect(cleaned.image))


class Score:
    def __init__(self):
        self.hit = self.true = self.said = self.exact = self.n = 0
        self.seconds = []

    def add(self, gt: Counter, pred: Counter, seconds: float):
        self.hit += sum((gt & pred).values())
        self.true += sum(gt.values())
        self.said += sum(pred.values())
        self.exact += +gt == +pred
        self.n += 1
        self.seconds.append(seconds)

    def result(self) -> dict:
        r = lambda a, b: round(a / b, 3) if b else None
        return {"count_recall": r(self.hit, self.true), "count_precision": r(self.hit, self.said),
                "exact_sketches": r(self.exact, self.n),
                "seconds_per_sketch": round(sum(self.seconds) / len(self.seconds), 2) if self.seconds else None}


async def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--images", default=str(ROOT / "datasets/synthetic/images/val"))
    ap.add_argument("--labels", default=str(ROOT / "datasets/synthetic/labels/val"))
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--pause", type=float, default=6, help="seconds between LLM calls (free-tier rate limits)")
    ap.add_argument("--json", help="also write the results to this file")
    args = ap.parse_args()
    if not settings.LLM_VISION_MODEL:
        sys.exit("Set LLM_VISION_MODEL in .env first")

    llm, pipe, failed = Score(), Score(), 0
    answered_llm, answered_pipe = Score(), Score()  # only the sketches the LLM actually answered
    for img in sorted(Path(args.images).glob("*.jpg"))[: args.limit]:
        gt = gt_counts(Path(args.labels) / f"{img.stem}.txt")
        start = time.perf_counter()
        ok = True
        try:
            pred = await ask_llm(img)
        except (llm_service.LLMUnavailable, ValueError, AttributeError) as e:  # a refusal or broken JSON counts as finding nothing
            print(f"{img.stem}: LLM failed ({str(e)[:80]})", file=sys.stderr)
            pred, failed, ok = Counter(), failed + 1, False
        llm_seconds = time.perf_counter() - start
        start = time.perf_counter()
        mine = ours(img)
        pipe_seconds = time.perf_counter() - start
        llm.add(gt, pred, llm_seconds)
        pipe.add(gt, mine, pipe_seconds)
        if ok:
            answered_llm.add(gt, pred, llm_seconds)
            answered_pipe.add(gt, mine, pipe_seconds)
        await asyncio.sleep(args.pause)

    results = {"images": llm.n, "llm_model": settings.LLM_VISION_MODEL, "llm_failed_replies": failed,
               "vision_llm_only": llm.result(), "sketch2ui_detector": pipe.result(),
               "answered_only": {"images": answered_llm.n, "vision_llm_only": answered_llm.result(),
                                 "sketch2ui_detector": answered_pipe.result()}}
    print(json.dumps(results, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
