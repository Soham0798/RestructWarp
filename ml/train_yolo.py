"""Train the sketch detector (Step 16). Runs on Kaggle's free GPU or, slowly, on a laptop CPU.

    python ml/train_yolo.py --data datasets/synthetic/data.yaml --epochs 100            # Kaggle GPU
    python ml/train_yolo.py --data datasets/synthetic/data.yaml --epochs 5 --device cpu # quick local check

The best weights are copied to weights/sketch_yolo.pt, where detect.py loads them.
"""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(ROOT / "datasets" / "synthetic" / "data.yaml"))
    ap.add_argument("--model", default="yolov8n.pt", help="start from pretrained weights (n = smallest, fastest)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=960, help="sketches have small parts, so larger than the usual 640")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default=None, help="0 for the first GPU, cpu to force CPU")
    ap.add_argument("--out", default=str(ROOT / "weights" / "sketch_yolo.pt"))
    args = ap.parse_args()

    from ultralytics import YOLO  # imported here so --help works without the heavy package

    model = YOLO(args.model)
    model.train(
        data=args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch, device=args.device,
        project=str(ROOT / "runs"), name="sketch", exist_ok=True,
        fliplr=0.0,   # mirrored text and arrows would teach the wrong shapes
        mosaic=0.5, degrees=3, perspective=0.0005, hsv_v=0.3,  # mild camera-like variation
        patience=25, plots=True,
    )
    best = Path(model.trainer.best)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, args.out)
    metrics = model.val(data=args.data, imgsz=args.imgsz, device=args.device)
    print(f"Saved {args.out}  mAP50={metrics.box.map50:.3f}  mAP50-95={metrics.box.map:.3f}")


if __name__ == "__main__":
    main()
