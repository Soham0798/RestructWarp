"""Step 18: find UI elements, arrows and notes with the trained YOLO model."""
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.services.vision.types import Detection

WEIGHTS = Path(__file__).resolve().parents[3] / "weights" / "sketch_yolo.pt"
MIN_CONF = 0.35


class DetectorUnavailable(RuntimeError):
    """No trained weights yet (train with ml/train_yolo.py) or ultralytics is not installed."""


@lru_cache(maxsize=1)
def _model(path: str):
    if not Path(path).exists():
        raise DetectorUnavailable(f"No weights at {path}; train with ml/train_yolo.py")
    try:
        from ultralytics import YOLO  # heavy import, done once on first use
    except ImportError as e:
        raise DetectorUnavailable("pip install -r requirements-vision.txt") from e
    return YOLO(path)


def detect(img: np.ndarray, weights: Path = WEIGHTS, min_conf: float = MIN_CONF, imgsz: int = 960) -> list[Detection]:
    model = _model(str(weights))
    result = model.predict(img, imgsz=imgsz, conf=min_conf, verbose=False)[0]
    names = result.names
    out = []
    for (x1, y1, x2, y2), cls, conf in zip(result.boxes.xyxy.tolist(), result.boxes.cls.tolist(),
                                           result.boxes.conf.tolist()):
        out.append(Detection(names[int(cls)], x1, y1, x2, y2, float(conf)))
    return out
