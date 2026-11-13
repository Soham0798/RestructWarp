"""Steps 40-43: score the pipeline on a labelled test set the detector never trained on.

    python ml/evaluate.py --images datasets/synthetic/images/val --labels datasets/synthetic/labels/val
    python ml/evaluate.py ... --no-preprocess        # ablation: skip shadow removal / deskew
    python ml/evaluate.py ... --ocr                  # also score the text OCR read (slow on CPU)
    python ml/evaluate.py ... --photo                # distort inputs like phone photos first
    python ml/evaluate.py ... --json results.json    # save numbers for the report

Metrics (all 0-1, higher is better):
  precision / recall     detected boxes matching a true box (IoU >= 0.5), any class
  component_accuracy     true boxes found AND given the right type
  layout_iou             mean overlap of matched boxes (position accuracy)
  link_accuracy          drawn arrows that became the right screen -> screen link (F2)
  note_recall            handwritten notes that were detected (F3)
  text_accuracy          (--ocr) drawn words that ended up in the right element's text
  note_accuracy          (--ocr) notes whose word reached the element they were written beside (F3)
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.vision import detect, layout, notes, ocr, preprocess  # noqa: E402
from app.services.vision.types import Detection  # noqa: E402

CLASSES = json.loads((ROOT / "shared" / "detector_classes.json").read_text())


def iou(a: Detection, b: Detection) -> float:
    w = min(a.x2, b.x2) - max(a.x1, b.x1)
    h = min(a.y2, b.y2) - max(a.y1, b.y1)
    inter = max(0, w) * max(0, h)
    union = a.area + b.area - inter
    return inter / union if union else 0.0


def read_labels(path: Path, w: int, h: int, scale: float = 1.0) -> list[Detection]:
    dets = []
    for line in path.read_text().split("\n"):
        if line.strip():
            c, cx, cy, bw, bh = line.split()
            cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
            dets.append(Detection(CLASSES[int(c)], (cx - bw / 2) * scale, (cy - bh / 2) * scale,
                                  (cx + bw / 2) * scale, (cy + bh / 2) * scale))
    return dets


def match(gt: list[Detection], pred: list[Detection], thr: float = 0.5):
    """Greedy one-to-one matching by IoU, best pairs first."""
    pairs = sorted(((iou(g, p), i, j) for i, g in enumerate(gt) for j, p in enumerate(pred)), reverse=True)
    used_g, used_p, out = set(), set(), []
    for v, i, j in pairs:
        if v < thr:
            break
        if i not in used_g and j not in used_p:
            used_g.add(i)
            used_p.add(j)
            out.append((gt[i], pred[j], v))
    return out


def read_words(path: Path, w: int, h: int, scale: float = 1.0) -> list[Detection]:
    """The generator's answer key: every word it wrote, as a box whose text is the word."""
    if not path.exists():
        return []
    return [Detection("line", x1 * w * scale, y1 * h * scale, x2 * w * scale, y2 * h * scale, text=item["word"])
            for item in json.loads(path.read_text()) for x1, y1, x2, y2 in [item["box"]]]


def read_ignore(path: Path, w: int, h: int, scale: float = 1.0) -> list[Detection]:
    """Regions whose objects we have no class for (e.g. SketchFlow's charts): not scored either way."""
    if not path.exists():
        return []
    return [Detection("ignore", x1 * w * scale, y1 * h * scale, x2 * w * scale, y2 * h * scale)
            for x1, y1, x2, y2 in json.loads(path.read_text())]


def outside(pred: list[Detection], ignore: list[Detection]) -> list[Detection]:
    return [p for p in pred if not any(g.x1 <= p.center[0] <= g.x2 and g.y1 <= p.center[1] <= g.y2 for g in ignore)]


def holder(word: Detection, dets: list[Detection]):
    """The smallest text-bearing box holding the word's centre (where OCR should put it)."""
    cx, cy = word.center
    inside = [d for d in dets if d.cls in ocr.TEXT_BEARING and d.x1 <= cx <= d.x2 and d.y1 <= cy <= d.y2]
    return min(inside, key=lambda d: d.area) if inside else None


def elements(dets: list[Detection]) -> list[Detection]:
    """What layout.build_document hands to notes.attach (screens aside, which are never nearest)."""
    return [d for d in dets if d.cls not in ("arrow", "note")]


def text_scores(gt, pred, pairs, words) -> tuple[int, int, int, int]:
    """(words, words read into the right box, notes, notes attached to the right element)."""
    to_pred = {id(g): p for g, p, _ in pairs}
    said = lambda d, word: word.lower() in d.text.lower()
    n_words = n_ok = n_notes = n_notes_ok = 0
    for word in words:
        g = holder(word, gt)
        if g is None:
            continue
        n_words += 1
        p = to_pred.get(id(g))
        n_ok += bool(p and said(p, word.text))
        if g.cls == "note":
            n_notes += 1
            target = notes.nearest(g, elements(gt))
            got = notes.nearest(p, elements(pred)) if p and said(p, word.text) else None
            n_notes_ok += bool(target and got and iou(target, got) >= 0.5)
    return n_words, n_ok, n_notes, n_notes_ok


def as_photo(img: np.ndarray, rng: random.Random) -> tuple[np.ndarray, float]:
    """Tilt, shade, blur and add sensor noise the way a phone camera would. Returns (image, tilt)."""
    h, w = img.shape[:2]
    tilt = rng.uniform(-8, 8)
    img = preprocess.rotate(img, tilt)
    gx = np.linspace(rng.uniform(0.5, 0.8), 1.0, w)[None, :]
    gy = np.linspace(1.0, rng.uniform(0.75, 1.0), h)[:, None]
    img = (img * (gx * gy)[..., None]).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    noise = np.random.default_rng(rng.randrange(1 << 30)).normal(0, 6, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8), tilt


def rotate_boxes(boxes: list[Detection], angle: float, w: int, h: int) -> list[Detection]:
    """Turn answer-key boxes by the same angle as preprocess.rotate, keeping each one upright."""
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    out = []
    for b in boxes:
        pts = np.array([[b.x1, b.y1, 1], [b.x2, b.y1, 1], [b.x1, b.y2, 1], [b.x2, b.y2, 1]]) @ m.T
        out.append(Detection(b.cls, pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max(), text=b.text))
    return out


def screen_links(dets, w, h) -> set:
    doc = layout.build_document(dets, w, h)
    order = {s.id: i for i, s in enumerate(doc.screens)}
    return {(order[l.fromScreen], order[l.toScreen]) for l in doc.links}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--images", default=str(ROOT / "datasets/synthetic/images/val"))
    ap.add_argument("--labels", default=str(ROOT / "datasets/synthetic/labels/val"))
    ap.add_argument("--weights", default=str(detect.WEIGHTS))
    ap.add_argument("--no-preprocess", action="store_true")
    ap.add_argument("--ocr", action="store_true", help="also run OCR and score text + notes")
    ap.add_argument("--photo", action="store_true", help="tilt, shade, blur and add noise first")
    ap.add_argument("--limit", type=int, help="only the first N images")
    ap.add_argument("--json", help="also write the results to this file")
    args = ap.parse_args()

    tot = {k: 0 for k in ("gt", "pred", "matched", "typed", "links_gt", "links_ok", "notes_gt", "notes_ok",
                          "words", "words_ok", "notes_txt", "notes_txt_ok")}
    rng = random.Random(23)
    ious, seconds = [], []
    images = sorted(p for p in Path(args.images).iterdir() if p.suffix.lower() in (".jpg", ".png", ".jpeg"))
    images = images[: args.limit] if args.limit else images
    for img_path in images:
        raw = cv2.imread(str(img_path))
        tilt = 0.0
        if args.photo:
            raw, tilt = as_photo(raw, rng)
        start = time.perf_counter()
        if args.no_preprocess:
            img, plain, scale = raw, raw, 1.0
        else:
            cleaned = preprocess.clean(raw)
            img, plain, scale = cleaned.image, cleaned.plain, cleaned.scale
        pred = detect.detect(img, weights=Path(args.weights))
        if args.ocr:
            ocr.read_text(plain, pred)
        seconds.append(time.perf_counter() - start)
        h, w = img.shape[:2]
        gt = read_labels(Path(args.labels) / f"{img_path.stem}.txt", raw.shape[1], raw.shape[0], scale)
        words = read_words(Path(args.labels).parents[1] / "text" / Path(args.labels).name / f"{img_path.stem}.json",
                           raw.shape[1], raw.shape[0], scale)
        ignore = read_ignore(Path(args.labels).parents[1] / "ignore" / Path(args.labels).name / f"{img_path.stem}.json",
                             raw.shape[1], raw.shape[0], scale)
        pred = outside(pred, ignore)
        if args.photo:  # the answer key is upright; turn it by whatever tilt deskew left behind
            left = tilt + (0.0 if args.no_preprocess else cleaned.angle)
            gt, words = rotate_boxes(gt, left, w, h), rotate_boxes(words, left, w, h)

        pairs = match(gt, pred)
        tot["gt"] += len(gt)
        tot["pred"] += len(pred)
        tot["matched"] += len(pairs)
        tot["typed"] += sum(1 for g, p, _ in pairs if g.cls == p.cls)
        ious += [v for *_, v in pairs]

        gl, pl = screen_links(gt, w, h), screen_links(pred, w, h)
        tot["links_gt"] += len(gl)
        tot["links_ok"] += len(gl & pl)
        gnotes = [g for g in gt if g.cls == "note"]
        tot["notes_gt"] += len(gnotes)
        tot["notes_ok"] += len(match(gnotes, [p for p in pred if p.cls == "note"], 0.3))
        if args.ocr:
            for k, v in zip(("words", "words_ok", "notes_txt", "notes_txt_ok"), text_scores(gt, pred, pairs, words)):
                tot[k] += v

    ratio = lambda a, b: round(tot[a] / tot[b], 3) if tot[b] else None
    results = {
        "images": len(images), "preprocess": not args.no_preprocess, "photo": args.photo,
        "precision": ratio("matched", "pred"), "recall": ratio("matched", "gt"),
        "component_accuracy": ratio("typed", "gt"),
        "layout_iou": round(sum(ious) / len(ious), 3) if ious else None,
        "link_accuracy": ratio("links_ok", "links_gt"), "note_recall": ratio("notes_ok", "notes_gt"),
        "seconds_per_sketch": round(sum(seconds) / len(seconds), 2) if seconds else None,
    }
    if args.ocr:
        results |= {"text_accuracy": ratio("words_ok", "words"), "note_accuracy": ratio("notes_txt_ok", "notes_txt")}
    print(json.dumps(results, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
