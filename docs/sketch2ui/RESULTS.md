# Evaluation results

## Headline: real hand-drawn wireframes

**Test set:** 40 real pen-on-paper wireframes from the public SketchFlow dataset (Zulvani & Tyas,
Universitas Gadjah Mada, 2025, CC BY 4.0, doi:10.17632/nssnvc96g9.1). There are 8 screen designs, each
drawn by 5 people. Neither the designs nor these drawings were used in training (`ml/import_sketchflow.py`
splits by design). SketchFlow's 27 classes are mapped onto our 14. Tables, charts, sliders, lists and alerts
have no Sketch2UI type; they are 9% of boxes and are excluded from scoring in both directions.

| Detector | Precision | Recall | Right box + right type | Layout IoU |
|---|---|---|---|---|
| v1: trained on 521 synthetic sketches only | 0.513 | 0.467 | 0.128 | 0.803 |
| v2: fine-tuned on synthetic + 75 real drawings (×4) | 0.865 | 0.830 | 0.765 | 0.898 |
| **v3: v2 + generator draws image-cards, radios, switches, filled checkboxes** | **0.879** | **0.868** | **0.793** | **0.904** |
| v3 on the same 40 drawings as phone photos (`--photo`) | 0.898 | 0.878 | 0.777 | 0.895 |

All versions still score ≈0.997 component accuracy on the synthetic test set, so the real data didn't
cost anything there. Fine-tunes: 60 epochs each on Kaggle (T4, ~16 min); the best epoch is chosen on 2
held-back *training* designs, never on the test set (`ml/prepare_finetune.py`). v3 is the live model.

**Per type on the real test (v2 → v3):**

| Type | Count | Found | Right type |
|---|---|---|---|
| text | 126 | 0.87 → 0.88 | 0.87 → 0.88 |
| button | 95 | 0.86 → 0.85 | 0.80 → 0.79 |
| card | 90 | 0.61 → **0.78** | 0.53 → **0.68** |
| checkbox (incl. radio, switch) | 77 | 0.82 → 0.87 | 0.60 → 0.64 |
| input (incl. password, date, time) | 50 | 0.98 → 0.98 | 0.98 → 0.92 |
| image | 35 | 0.86 → 0.86 | 0.86 → 0.83 |
| dropdown | 20 | 1.00 → 1.00 | 0.90 → 1.00 |

v2's weak spots were SketchFlow's "image-card" style and its radio and switch drawings, which our generator
never drew. Teaching the generator those styles (v3) fixed most of the card gap. Checkboxes are still
confused with buttons (16 of 77): they are tiny, and some real drawings of switches look like small buttons.
More real drawings of toggles would help most.

**Lesson for the report:** synthetic data alone gave 0.997 on synthetic tests but only 0.128 on real
drawings. 75 real drawings, repeated in training, closed most of that gap. Report the real numbers.

---

## Synthetic test set (details and ablations)

Detector v1: YOLOv8n trained 100 epochs on Kaggle (2 × T4, 20 min) on 521 synthetic sketches.
Test set: 79 synthetic sketches never used for training (`datasets/synthetic/*/val`), scored with
`ml/evaluate.py`. The generator also saves every word it wrote, so text and notes are scored against
the true words. Raw numbers are in the `.json` files next to this one.

**Phone photo** means `--photo`: each test image is tilted ±8°, shaded unevenly (down to 50% brightness),
blurred and given sensor noise, to mimic a phone picture of paper.

## Main results

| Metric | Clean scan | Phone photo |
|---|---|---|
| YOLO mAP50 / mAP50-95 (Ultralytics val) | 0.995 / 0.943 | – |
| Precision | 0.996 | 0.997 |
| Recall | 0.998 | 0.999 |
| Component accuracy (right box, right type) | 0.997 | 0.996 |
| Layout IoU (position accuracy) | 0.955 | 0.954 |
| Link accuracy, arrows → screen links (F2) | 1.000 | 1.000 |
| Note detection recall (F3) | 1.000 | 1.000 |
| Text accuracy: drawn words that reach the right element (30 sketches) | 0.905 | 0.681 |
| Note accuracy: note text attached to the right element (F3, 30 sketches) | 0.719 | 0.375 |
| Time per sketch, detection only (CPU laptop) | 0.48 s | 0.45 s |
| Time per sketch with OCR (CPU laptop) | 21 s (now ~5 s, see OCR speed) | 20 s (now 4.7 s) |

**Reading the table:** finding and placing elements is solved on this data, even on photos. Reading
handwriting is the weak link: about 1 word in 3 is lost on photos, and short notes ("red", "big") suffer
most. The LLM refine step and the editable JSON tab are where a user fixes these.

## Ablation 1: preprocessing (Step 43)

| Input | Preprocessing | Component accuracy | Layout IoU | Text accuracy | Note accuracy |
|---|---|---|---|---|---|
| Clean scan | full | 0.997 | 0.955 | 0.905 | 0.719 |
| Clean scan | none | 0.996 | 0.956 | – | – |
| Phone photo | full | 0.996 | 0.954 | 0.681 | 0.375 |
| Phone photo | none | 0.996 | 0.963 | 0.684 | 0.406 |

On this data preprocessing makes no measurable difference: the detector copes with ±8° tilt and
shading by itself (training included shading and blur). It is kept because real photos can be worse:
stronger tilt, hard shadows from a phone or hand. Re-run this table on the real test set before
drawing conclusions. OCR reads the deskewed image *without* shadow removal (see Ablation 2).

## Ablation 2: OCR fixes found in Step 23

Phone photos, first 15 test sketches. Each row adds one fix to the row above.

| Version | Text accuracy | Note accuracy |
|---|---|---|
| OCR as first written | 0 (crashed on Windows: Paddle 3.3 oneDNN bug) | 0 |
| + oneDNN off, contrast stretch before OCR | 0.623 | 0.133 |
| + split OCR lines word by word, notes attach to the element on their row | 0.636 | 0.267 |
| + OCR reads the image before shadow removal | 0.679 | 0.400 |

The word split matters because OCR joins a label and the note written beside it into one line
("Sign up green"). Shadow removal divides by the estimated lighting, which also amplifies camera noise:
fine for the detector, bad for reading thin handwriting.

## Ablation 3: deskew

| Version | Component accuracy | Note |
|---|---|---|
| First deskew (median of line angles) | 0.869 | Rotated 12/79 straight sketches by 6–15°, fooled by image-placeholder diagonals and arrows |
| Fixed deskew (length-weighted dominant direction) | 0.997 | 0/79 false rotations; tilted photos still straightened (tests) |

## Still to do

- **Our own team's sketches (Steps 11, 14).** SketchFlow now gives a real test set, but its drawings
  have no handwritten labels, arrows or notes. Photos of our own multi-screen sketches would test text, links and notes on real data.
- **OCR speed: fixed.** OCR took about 20 s per sketch on a laptop CPU because Paddle's own CPU engine
  runs without oneDNN (which crashes on Windows). The same PP-OCRv6 medium models now run on ONNX Runtime
  (`OCR_ENGINE=onnxruntime`, the default). Phone photos, first 15 test sketches, laptop plugged in:

  | OCR setup | Time per sketch | Text accuracy | Note accuracy |
  |---|---|---|---|
  | **PP-OCRv6 medium, ONNX Runtime (default)** | **4.7 s** | **0.691** | **0.400** |
  | PP-OCRv6 medium, Paddle engine (before) | 19.4 s | 0.698 | 0.400 |
  | Medium, Paddle, detection on image shrunk to 736 px | 9.9 s | 0.611 | 0.333 |
  | PP-OCRv6 tiny, Paddle | 3.6 s | 0.438 | 0.333 |
  | PP-OCRv5 mobile, Paddle | 6.2 s | 0.432 | 0.267 |

  Same models, so accuracy stays the same; shrinking the image or switching to a lighter model loses words.
