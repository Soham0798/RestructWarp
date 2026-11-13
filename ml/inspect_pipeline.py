"""Step 23: run photo -> UIDocument on a handful of sketches and save what the pipeline saw.

    python ml/inspect_pipeline.py --n 10                     # 10 val sketches -> runs/inspect/
    python ml/inspect_pipeline.py --n 10 --photo             # same, made to look like phone photos
    python ml/inspect_pipeline.py --images my_photos/        # your own sketches

For each sketch it writes <name>.json (the UIDocument) and <name>.png (boxes, types and the
text OCR read, drawn over the cleaned image), then prints one summary line so mistakes stand out.
"""
import argparse
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.vision import detect, layout, ocr, preprocess  # noqa: E402
from evaluate import as_photo  # noqa: E402

COLORS = {"screen": (160, 160, 160), "arrow": (0, 140, 255), "note": (200, 0, 200)}


def draw(img: np.ndarray, dets) -> np.ndarray:
    out = img.copy()
    for d in dets:
        color = COLORS.get(d.cls, (0, 160, 0))
        p1, p2 = (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2))
        cv2.rectangle(out, p1, p2, color, 2)
        label = f"{d.cls} {d.conf:.2f}" + (f" '{d.text}'" if d.text else "")
        cv2.putText(out, label, (p1[0], max(12, p1[1] - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--images", default=str(ROOT / "datasets/synthetic/images/val"))
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--photo", action="store_true", help="distort the inputs like phone photos first")
    ap.add_argument("--out", default=str(ROOT / "runs/inspect"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(23)
    images = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in (".jpg", ".png", ".jpeg"))
    for img_path in images[: args.n]:
        raw = cv2.imread(str(img_path))
        if args.photo:
            raw, _ = as_photo(raw, rng)
        cleaned = preprocess.clean(raw)
        dets = detect.detect(cleaned.image)
        try:
            ocr.read_text(cleaned.plain, dets)
        except ocr.OCRUnavailable:
            pass
        h, w = cleaned.image.shape[:2]
        doc = layout.build_document(dets, w, h, name=img_path.stem)

        (out / f"{img_path.stem}.json").write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        cv2.imwrite(str(out / f"{img_path.stem}.png"), draw(cleaned.image, dets))
        unlabeled = sum(1 for d in dets if d.cls in ("button", "heading", "input") and not d.text)
        print(f"{img_path.stem}: tilt {cleaned.angle:+.1f}  boxes {len(dets)}  screens {len(doc.screens)}  "
              f"links {len(doc.links)}  forms {sum(1 for s in doc.screens for c in s.root.walk() if c.form)}  "
              f"unlabeled {unlabeled}  low-conf {sum(1 for d in dets if d.conf < 0.5)}")
    print(f"saved to {out}")


if __name__ == "__main__":
    main()
