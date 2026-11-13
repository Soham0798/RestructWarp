"""Build the fine-tune data: synthetic sketches + real SketchFlow wireframes (Step 16, second round).

    python ml/prepare_finetune.py --synthetic datasets/synthetic --real datasets/sketchflow_real --out datasets/finetune

Real drawings are few (75), so their list is repeated so each epoch sees them as often as ~300 synthetic
ones. Two real *training* designs are held back for choosing the best epoch; the 40-image real test
set is never touched, so its score stays honest.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSES = json.loads((ROOT / "shared" / "detector_classes.json").read_text())
REAL_VAL_DESIGNS = ("test-mobile-9-", "test-desktop-7-")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--synthetic", default=str(ROOT / "datasets/synthetic"))
    ap.add_argument("--real", default=str(ROOT / "datasets/sketchflow_real"))
    ap.add_argument("--out", default=str(ROOT / "datasets/finetune"))
    ap.add_argument("--repeat", type=int, default=4, help="times each real training image is listed")
    args = ap.parse_args()

    syn, real, out = Path(args.synthetic).resolve(), Path(args.real).resolve(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    real_train = sorted((real / "images/train").glob("*.jpg"))
    held = [p for p in real_train if p.name.startswith(REAL_VAL_DESIGNS)]
    fit = [p for p in real_train if p not in held]
    train = sorted((syn / "images/train").glob("*.jpg")) + fit * args.repeat
    val = sorted((syn / "images/val").glob("*.jpg"))[:40] + held
    (out / "train.txt").write_text("\n".join(p.as_posix() for p in train) + "\n")
    (out / "val.txt").write_text("\n".join(p.as_posix() for p in val) + "\n")
    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\ntrain: train.txt\nval: val.txt\n"
        "names:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES)))
    print(f"train {len(train)} ({len(fit)} real x{args.repeat}), val {len(val)} ({len(held)} real)")


if __name__ == "__main__":
    main()
