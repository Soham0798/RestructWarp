"""Clean a sketch photo before detection: decode, resize, remove shadows, straighten (Step 17)."""
from dataclasses import dataclass

import cv2
import numpy as np

MAX_SIDE = 1600  # bigger photos are shrunk; detail beyond this doesn't help detection


@dataclass
class Cleaned:
    image: np.ndarray  # BGR, ready for the detector
    plain: np.ndarray  # same size and angle, shadows left in: better for OCR (division amplifies noise)
    scale: float       # cleaned size / original size
    angle: float       # degrees the photo was rotated to straighten it


def load_image(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Not a readable image (use PNG, JPG or WEBP)")
    return img


def resize(img: np.ndarray) -> tuple[np.ndarray, float]:
    scale = min(1.0, MAX_SIDE / max(img.shape[:2]))
    if scale < 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img, scale


def remove_shadows(img: np.ndarray) -> np.ndarray:
    """Estimate the paper's uneven lighting and divide it out, leaving white paper and dark ink."""
    out = []
    for ch in cv2.split(img):
        background = cv2.medianBlur(cv2.dilate(ch, np.ones((7, 7), np.uint8)), 21)
        out.append(cv2.divide(ch, background, scale=255))
    return cv2.merge(out)


def estimate_skew(img: np.ndarray, max_skew: float = 15.0) -> float:
    """Angle (degrees) of the ink, from the dominant direction of long straight strokes.

    Box edges all share one direction; the diagonals of image placeholders and arrows don't.
    So take the peak of a length-weighted histogram, not the median of every line.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    # short segments too: hand-drawn edges wobble, so long straight runs are rare
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=50, minLineLength=gray.shape[1] // 20, maxLineGap=6)
    if lines is None:
        return 0.0
    segs = lines.reshape(-1, 4).astype(float)  # shape differs between OpenCV versions
    angles = np.degrees(np.arctan2(segs[:, 3] - segs[:, 1], segs[:, 2] - segs[:, 0]))
    angles = (angles + 45) % 90 - 45  # fold horizontal and vertical strokes onto one axis
    lengths = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    keep = np.abs(angles) <= max_skew
    if lengths[keep].sum() < gray.shape[1]:  # too little straight ink to trust an angle
        return 0.0
    hist, edges_ = np.histogram(angles[keep], bins=np.arange(-max_skew, max_skew + 0.5, 0.5), weights=lengths[keep])
    window = np.convolve(hist, np.ones(3), mode="same")  # wobbly strokes spread over neighbouring bins
    peak = int(window.argmax())
    if window[peak] < 0.3 * lengths[keep].sum():  # no clear dominant direction: leave the photo alone
        return 0.0
    in_peak = keep & (angles >= edges_[peak] - 0.5) & (angles <= edges_[peak + 1] + 0.5)
    return float(np.average(angles[in_peak], weights=lengths[in_peak]))


def rotate(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def clean(img: np.ndarray, max_skew: float = 15.0) -> Cleaned:
    plain, scale = resize(img)
    img = remove_shadows(plain)
    angle = estimate_skew(img, max_skew)
    if 0.5 < abs(angle) <= max_skew:  # tiny tilts aren't worth blurring the image for
        img, plain = rotate(img, angle), rotate(plain, angle)
    else:
        angle = 0.0
    return Cleaned(image=img, plain=plain, scale=scale, angle=angle)
