"""Generate synthetic hand-drawn UI sketches with YOLO labels (Step 13).

Each image holds 1-3 phone screens drawn with wobbly pen strokes. Screens can be
linked by arrows (F2) and elements can carry handwritten notes (F3). Labels use
the 14 classes in shared/detector_classes.json.

    python ml/synth_sketches.py --n 500 --out datasets/synthetic
    python ml/synth_sketches.py --n 4 --out datasets/preview --preview
"""
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLASSES = json.loads((ROOT / "shared" / "detector_classes.json").read_text())
CID = {name: i for i, name in enumerate(CLASSES)}

WORDS = ["Login", "Sign up", "Submit", "Next", "Home", "Profile", "Search", "Cart", "Buy now",
         "Email", "Password", "Name", "Settings", "Welcome", "Dashboard", "Orders", "Menu", "Save"]
NOTES = ["blue", "red", "big", "bold", "sticky", "rounded", "center", "dark", "green", "small"]
PEN_COLORS = [(25, 25, 25), (60, 40, 30), (120, 50, 20), (40, 40, 110), (70, 70, 70)]  # BGR
FONTS = [cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_PLAIN]


class Sketch:
    def __init__(self, w, h, rng):
        self.rng = rng
        self.img = self._paper(w, h)
        self.pen = rng.choice(PEN_COLORS)
        self.thick = rng.choice([1, 2, 2, 3])
        self.boxes = []  # (class_name, x1, y1, x2, y2)
        self.words = []  # (word, x1, y1, x2, y2): the answer key for OCR (uses no rng, so images don't change)

    def _paper(self, w, h):
        base = np.full((h, w, 3), self.rng.randint(225, 252), np.uint8)
        noise = np.random.default_rng(self.rng.random().__hash__() & 0xFFFF).normal(0, 4, (h, w, 1))
        img = np.clip(base + noise, 0, 255).astype(np.uint8)
        if self.rng.random() < 0.4:  # ruled notebook lines
            for y in range(self.rng.randint(20, 40), h, self.rng.randint(28, 40)):
                cv2.line(img, (0, y), (w, y), (215, 200, 170), 1)
        return img

    def _wobble(self, p, q, steps=None):
        (x1, y1), (x2, y2) = p, q
        steps = steps or max(2, int(np.hypot(x2 - x1, y2 - y1) / 18))
        pts = []
        for i in range(steps + 1):
            t = i / steps
            j = self.rng.uniform(-1.6, 1.6)
            pts.append((x1 + (x2 - x1) * t + j, y1 + (y2 - y1) * t + j))
        return np.array(pts, np.int32)

    def line(self, p, q, thick=None):
        cv2.polylines(self.img, [self._wobble(p, q)], False, self.pen, thick or self.thick, cv2.LINE_AA)

    def rect(self, x1, y1, x2, y2, rounded=False):
        o = lambda: self.rng.randint(-3, 3)  # corners overshoot like a real pen
        if rounded:
            cv2.rectangle(self.img, (x1, y1), (x2, y2), self.pen, self.thick, cv2.LINE_AA)
            return
        self.line((x1 + o(), y1), (x2 + o(), y1))
        self.line((x2, y1 + o()), (x2, y2 + o()))
        self.line((x2 + o(), y2), (x1 + o(), y2))
        self.line((x1, y2 + o()), (x1, y1 + o()))

    def text(self, s, x, y, scale=0.6):
        font = self.rng.choice(FONTS)
        scale *= 1.4 if font == cv2.FONT_HERSHEY_PLAIN else 1
        weight = max(1, self.thick - 1)
        cv2.putText(self.img, s, (x, y), font, scale, self.pen, weight, cv2.LINE_AA)
        (tw, th), base = cv2.getTextSize(s, font, scale, weight)  # measure exactly what was drawn
        self.words.append((s, x, y - th, x + tw, y + base))
        return tw, th

    def scribble(self, x1, y, x2):
        """Wavy line standing in for a paragraph of text."""
        xs = np.arange(x1, x2, 4)
        ys = y + 3 * np.sin(xs / self.rng.uniform(3, 6))
        cv2.polylines(self.img, [np.stack([xs, ys], 1).astype(np.int32)], False, self.pen, 1, cv2.LINE_AA)

    def ellipse(self, cx, cy, rx, ry, filled=False):
        """Hand-drawn oval: radius wobbles a little and the stroke may not quite close."""
        t = np.linspace(0, 2 * np.pi * self.rng.uniform(0.95, 1.05), 28)
        r = 1 + np.array([self.rng.uniform(-0.06, 0.06) for _ in t])
        pts = np.stack([cx + rx * r * np.cos(t), cy + ry * r * np.sin(t)], 1).astype(np.int32)
        if filled:
            cv2.fillPoly(self.img, [pts], self.pen, cv2.LINE_AA)
        cv2.polylines(self.img, [pts], False, self.pen, self.thick, cv2.LINE_AA)

    def fill(self, x1, y1, x2, y2, hatch=False):
        """Solid fill, or quick diagonal scribbles the way people shade by hand."""
        if not hatch:
            cv2.rectangle(self.img, (x1, y1), (x2, y2), self.pen, -1)
            return
        for k in range(0, (x2 - x1) + (y2 - y1), 4):
            cv2.line(self.img, (x1 + min(k, x2 - x1), y1 + max(0, k - (x2 - x1))),
                     (x1 + max(0, k - (y2 - y1)), y1 + min(k, y2 - y1)), self.pen, 1, cv2.LINE_AA)

    def add(self, cls, x1, y1, x2, y2):
        self.boxes.append((cls, int(x1), int(y1), int(x2), int(y2)))


def draw_screen(sk, x, y, w, h, rng):
    """Draw one phone screen; returns the boxes of buttons (arrow start points)."""
    sk.rect(x, y, x + w, y + h)
    sk.add("container", x, y, x + w, y + h)
    pad, cy, buttons = int(w * 0.07), y + 8, []

    if rng.random() < 0.8:  # navbar with a logo box and menu lines
        nh = int(h * 0.09)
        sk.rect(x + 4, cy, x + w - 4, cy + nh)
        sk.rect(x + 10, cy + 6, x + 10 + nh - 12, cy + nh - 6)
        for k in range(3):
            sk.line((x + w - 34, cy + 10 + k * 7), (x + w - 14, cy + 10 + k * 7), 1)
        sk.add("navbar", x + 4, cy, x + w - 4, cy + nh)
        cy += nh + 12

    bottom = y + h - (int(h * 0.09) + 10)
    while cy < bottom - 40:
        kind = rng.choices(["heading", "text", "button", "input", "textarea", "image", "checkbox", "dropdown", "card"],
                           [2, 3, 3, 3, 1, 2, 2, 1, 2])[0]  # toggles and cards up: they were weakest on real drawings
        x1, x2 = x + pad, x + w - pad
        if kind == "heading":
            tw, th = sk.text(rng.choice(WORDS), x1, cy + 24, 0.9)
            sk.add("heading", x1 - 2, cy + 24 - th - 4, x1 + tw + 4, cy + 30)
            cy += 40
        elif kind == "text":
            n = rng.randint(1, 3)
            for k in range(n):
                sk.scribble(x1, cy + 8 + k * 12, x2 - rng.randint(0, w // 4))
            sk.add("text", x1, cy, x2, cy + 14 + (n - 1) * 12)
            cy += 22 + (n - 1) * 12
        elif kind in ("button", "input"):
            bh = rng.randint(26, 36)
            bx2 = x2 if kind == "input" or rng.random() < 0.6 else x1 + int((x2 - x1) * 0.5)
            sk.rect(x1, cy, bx2, cy + bh, rounded=kind == "button" and rng.random() < 0.3)
            word = rng.choice(WORDS)
            tw, _ = cv2.getTextSize(word, FONTS[0], 0.5, 1)[0]
            tx = x1 + 8 if kind == "input" else max(x1 + 4, (x1 + bx2 - tw) // 2)
            sk.text(word, tx, cy + bh - 9, 0.5)
            sk.add(kind, x1, cy, bx2, cy + bh)
            if kind == "button":
                buttons.append((x1, cy, bx2, cy + bh))
            cy += bh + 12
        elif kind == "textarea":
            th = rng.randint(50, 80)
            sk.rect(x1, cy, x2, cy + th)
            sk.line((x2 - 10, cy + th - 4), (x2 - 4, cy + th - 10), 1)
            sk.add("textarea", x1, cy, x2, cy + th)
            cy += th + 12
        elif kind == "image":
            ih = rng.randint(50, 100)
            sk.rect(x1, cy, x2, cy + ih)
            sk.line((x1, cy), (x2, cy + ih), 1)
            sk.line((x2, cy), (x1, cy + ih), 1)
            sk.add("image", x1, cy, x2, cy + ih)
            cy += ih + 12
        elif kind == "checkbox":  # also radios and switches: all toggles become a checkbox
            s = rng.randint(14, 26)
            style = rng.choice(["tick", "tick", "inner", "filled", "radio", "radio_dot", "switch", "switch_hatch"])
            bw = 2 * s if style.startswith("switch") else s
            q = s // 4
            if style.startswith("radio"):
                sk.ellipse(x1 + s // 2, cy + s // 2, s // 2, s // 2)
                sk.ellipse(x1 + s // 2, cy + s // 2, max(2, s // 6), max(2, s // 6), filled=style == "radio_dot")
            elif style == "switch":
                sk.rect(x1, cy, x1 + bw, cy + s, rounded=True)
                sk.ellipse(x1 + s // 2, cy + s // 2, s // 2 - 1, s // 2 - 1, filled=True)
            else:
                sk.rect(x1, cy, x1 + bw, cy + s)
                if style == "tick":
                    sk.line((x1 + 3, cy + s // 2), (x1 + s // 2 - 1, cy + s - 3), 1)
                    sk.line((x1 + s // 2 - 1, cy + s - 3), (x1 + s - 2, cy + 3), 1)
                elif style == "inner":
                    sk.rect(x1 + q, cy + q, x1 + s - q, cy + s - q)
                elif style == "filled":
                    sk.fill(x1 + q, cy + q, x1 + s - q, cy + s - q)
                else:  # hatched half of a switch
                    sk.fill(x1 + 2, cy + 2, x1 + s, cy + s - 2, hatch=True)
                    sk.line((x1 + s, cy), (x1 + s, cy + s), 1)
            sk.add("checkbox", x1, cy, x1 + bw, cy + s)
            if rng.random() < 0.75:
                sk.scribble(x1 + bw + 8, cy + s // 2, x1 + bw + 8 + rng.randint(40, 90))
            cy += s + 12
        elif kind == "dropdown":
            sk.rect(x1, cy, x2, cy + 28)
            sk.line((x2 - 22, cy + 10), (x2 - 15, cy + 18), 1)
            sk.line((x2 - 15, cy + 18), (x2 - 8, cy + 10), 1)
            sk.add("dropdown", x1, cy, x2, cy + 28)
            cy += 40
        elif kind == "card" and rng.random() < 0.5:  # image cards: crossed picture over a caption strip, 1-3 in a row
            n, gap = rng.choice([1, 2, 3]), 10
            cw, ch = (x2 - x1 - gap * (n - 1)) // n, min(rng.randint(70, 130), bottom - cy)  # stay above the footer
            for k in range(n):
                cx1 = x1 + k * (cw + gap)
                strip = cy + int(ch * rng.uniform(0.7, 0.82))
                sk.rect(cx1, cy, cx1 + cw, cy + ch)
                sk.line((cx1, cy), (cx1 + cw, strip), 1)
                sk.line((cx1 + cw, cy), (cx1, strip), 1)
                sk.line((cx1, strip), (cx1 + cw, strip), 1)
                sk.scribble(cx1 + 6, (strip + cy + ch) // 2, cx1 + cw - 8)
                sk.add("card", cx1, cy, cx1 + cw, cy + ch)
            cy += ch + 12
        elif kind == "card":
            ch = rng.randint(60, 90)
            sk.rect(x1, cy, x2, cy + ch)
            sk.text(rng.choice(WORDS), x1 + 8, cy + 22, 0.55)
            sk.scribble(x1 + 8, cy + 40, x2 - 12)
            sk.add("card", x1, cy, x2, cy + ch)
            cy += ch + 12

    if rng.random() < 0.6:  # footer
        fy = y + h - int(h * 0.08) - 4
        sk.rect(x + 4, fy, x + w - 4, y + h - 4)
        sk.add("footer", x + 4, fy, x + w - 4, y + h - 4)
    return buttons


def draw_arrow(sk, start, end):
    (x1, y1), (x2, y2) = start, end
    sk.line(start, end)
    ang = np.arctan2(y2 - y1, x2 - x1)
    for d in (2.6, -2.6):  # arrow head
        hx, hy = x2 + 14 * np.cos(ang + d), y2 + 14 * np.sin(ang + d)
        sk.line(end, (int(hx), int(hy)))
    xs, ys = [x1, x2], [y1, y2]
    sk.add("arrow", min(xs) - 8, min(ys) - 10, max(xs) + 8, max(ys) + 10)


def make_sketch(rng, size=(1280, 900)):
    w, h = size
    n_screens = rng.choices([1, 2, 3], [4, 4, 2])[0]
    sw = int(w / n_screens * rng.uniform(0.55, 0.68))
    sh = int(h * rng.uniform(0.78, 0.9))
    if n_screens == 1 and rng.random() < 0.6:
        sw = min(sw, int(sh * rng.uniform(0.5, 0.62)))  # phone-shaped rather than tablet-wide
    gap = (w - n_screens * sw) // (n_screens + 1)
    sk = Sketch(w, h, rng)

    screens = []
    for i in range(n_screens):
        sx = gap + i * (sw + gap) + rng.randint(-10, 10)
        sy = (h - sh) // 2 + rng.randint(-15, 15)
        screens.append((sx, sy, sw, sh, draw_screen(sk, sx, sy, sw, sh, rng)))

    for (ax, ay, aw, ah, buttons), (bx, by, bw, bh, _) in zip(screens, screens[1:]):
        if buttons and rng.random() < 0.85:  # F2: arrow from a button to the next screen
            b = rng.choice(buttons)
            draw_arrow(sk, (b[2] + 4, (b[1] + b[3]) // 2), (bx - 6, by + rng.randint(bh // 5, bh // 2)))

    targets = [b for b in sk.boxes if b[0] in ("button", "input", "heading", "card")]
    for cls, x1, y1, x2, y2 in rng.sample(targets, k=min(len(targets), rng.randint(0, 2))):  # F3: notes
        word = rng.choice(NOTES)
        nx, ny = x2 + 10, (y1 + y2) // 2 + 6
        tw, th = sk.text(word, nx, ny, 0.55)
        if nx + tw < w:
            sk.add("note", nx - 3, ny - th - 5, nx + tw + 3, ny + 6)
    return sk


def augment(img, rng):
    if rng.random() < 0.5:  # uneven lighting / shadow from a phone camera
        h, w = img.shape[:2]
        grad = np.tile(np.linspace(rng.uniform(0.6, 0.9), 1.0, w), (h, 1))
        if rng.random() < 0.5:
            grad = grad[:, ::-1]
        img = (img * grad[..., None]).astype(np.uint8)
    if rng.random() < 0.4:
        img = cv2.GaussianBlur(img, (3, 3), 0)
    if rng.random() < 0.3:
        img = cv2.convertScaleAbs(img, alpha=rng.uniform(0.85, 1.1), beta=rng.uniform(-15, 10))
    return img


def to_yolo(boxes, w, h):
    lines = []
    for cls, x1, y1, x2, y2 in boxes:
        x1, x2 = max(0, x1), min(w - 1, x2)
        y1, y2 = max(0, y1), min(h - 1, y2)
        if x2 - x1 < 3 or y2 - y1 < 3:
            continue
        lines.append(f"{CID[cls]} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--out", default="datasets/synthetic")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--val", type=float, default=0.15, help="share of images for validation")
    ap.add_argument("--preview", action="store_true", help="also save images with boxes drawn")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)
    for split in ("train", "val"):
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)

    for i in range(args.n):
        sk = make_sketch(rng)
        img = augment(sk.img, rng)
        split = "val" if rng.random() < args.val else "train"
        name = f"synth_{i:05d}"
        cv2.imwrite(str(out / "images" / split / f"{name}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        h, w = img.shape[:2]
        (out / "labels" / split / f"{name}.txt").write_text("\n".join(to_yolo(sk.boxes, w, h)) + "\n")
        (out / "text" / split).mkdir(parents=True, exist_ok=True)
        (out / "text" / split / f"{name}.json").write_text(json.dumps(
            [{"word": wd, "box": [x1 / w, y1 / h, x2 / w, y2 / h]} for wd, x1, y1, x2, y2 in sk.words]))
        if args.preview:
            (out / "preview").mkdir(exist_ok=True)
            prev = img.copy()
            for cls, x1, y1, x2, y2 in sk.boxes:
                cv2.rectangle(prev, (x1, y1), (x2, y2), (0, 160, 0), 1)
                cv2.putText(prev, cls, (x1, max(10, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 220), 1)
            cv2.imwrite(str(out / "preview" / f"{name}.jpg"), prev)

    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\ntrain: images/train\nval: images/val\n"
        f"names:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES)))
    print(f"Wrote {args.n} sketches to {out}")


if __name__ == "__main__":
    main()
