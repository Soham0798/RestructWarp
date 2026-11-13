"""Step 12: turn the public SketchFlow wireframes into our 14-class YOLO format.

SketchFlow (Zulvani & Tyas, Universitas Gadjah Mada, 2025; CC BY 4.0, doi:10.17632/nssnvc96g9.1)
has 125 real hand-drawn wireframes: 25 screen designs, each drawn by 5 people.

    python ml/import_sketchflow.py --src datasets/public/sketchflow --out datasets/sketchflow_real

Split by *screen design*, not by image: the test designs never appear in training, so the score
measures layouts (and drawings) the model has not seen. Their classes with no Sketch2UI equivalent
(tables, charts, sliders...) are written to ignore/<split>/<name>.json: evaluate.py neither rewards
nor penalises detections there.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = json.loads((ROOT / "shared" / "detector_classes.json").read_text())

MAP = {
    "label": "text", "hyperlink": "text",
    "common-button": "button", "icon-button": "button", "common-image-button": "button", "segmented-button": "button",
    "input-free-text": "input", "input-password": "input", "input-number": "input", "input-file": "input",
    "date-picker": "input", "time-picker": "input",
    "checkbox": "checkbox", "radio-button": "checkbox", "switch": "checkbox",
    "combobox": "dropdown", "textarea": "textarea", "image": "image", "image-card": "card",
}
IGNORE = {"alert", "list", "key-value", "table", "slider", "bar-chart", "line-chart", "pie-chart"}
TEST_SCREENS = {"mobile-11", "mobile-12", "mobile-13", "mobile-14", "mobile-15", "desktop-8", "desktop-9", "desktop-10"}


def elements(node):
    """Every {objClass, originalPosition} in SketchFlow's nested rows/cards JSON."""
    if isinstance(node, dict):
        if "objClass" in node and "originalPosition" in node:
            yield node
        for v in node.values():
            yield from elements(v)
    elif isinstance(node, list):
        for v in node:
            yield from elements(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", default=str(ROOT / "datasets/public/sketchflow"))
    ap.add_argument("--out", default=str(ROOT / "datasets/sketchflow_real"))
    args = ap.parse_args()
    out = Path(args.out)
    counts = {"train": 0, "val": 0}

    for folder in sorted((Path(args.src) / "WIREFRAME").glob("*-hand-*")):
        name = folder.name
        screen = re.match(r"test-((?:mobile|desktop)-\d+)-hand-", name).group(1)
        split = "val" if screen in TEST_SCREENS else "train"
        meta = json.loads((folder / f"{name}.json").read_text())
        w, h = meta["uiWidth"], meta["uiHeight"]
        labels, ignore = [], []
        for el in elements(meta):
            x1, y1, x2, y2 = el["originalPosition"]
            if el["objClass"] in IGNORE:
                ignore.append([x1 / w, y1 / h, x2 / w, y2 / h])
            else:
                cls = CLASSES.index(MAP[el["objClass"]])
                labels.append(f"{cls} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
        for sub in ("images", "labels", "ignore"):
            (out / sub / split).mkdir(parents=True, exist_ok=True)
        shutil.copy(folder / f"{name}.jpg", out / "images" / split / f"{name}.jpg")
        (out / "labels" / split / f"{name}.txt").write_text("\n".join(labels) + "\n")
        (out / "ignore" / split / f"{name}.json").write_text(json.dumps(ignore))
        counts[split] += 1

    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\ntrain: images/train\nval: images/val\n"
        "names:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES)))
    print(f"{counts['train']} train / {counts['val']} test wireframes -> {out}")


if __name__ == "__main__":
    main()
