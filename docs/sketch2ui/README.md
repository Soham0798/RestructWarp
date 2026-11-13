# Sketch2UI

**Draw your app on paper. Get working code.**

Sketch2UI turns a photo of a hand-drawn UI into accessible, multi-page code. Draw several screens,
link them with arrows, write notes like "blue" or "big" beside elements, and get HTML, a React project,
or a full-stack app whose forms already save to a database.

Minor project, built to merge into the major project **Restruct Warp** (see [docs/INTEGRATION.md](docs/INTEGRATION.md)).

## What it does

| Feature | |
|---|---|
| Sketch → UI | YOLO finds 12 kinds of element, PaddleOCR reads the handwriting, a layout step nests them |
| **F1** React export + QR | Download a runnable Vite + React + Tailwind project; scan a QR code to open the page on a phone |
| **F2** Multi-screen flows | Arrows drawn from a button to another screen become working links |
| **F3** Notes become styles | "blue", "rounded", "sticky" written beside an element are applied to it |
| **F4** Full stack | Every drawn form also gets a FastAPI + SQLite backend (passwords hashed) |
| **F5** Accessibility | axe-core scores each page; problems are fixed automatically and re-scored |

![Sketch Studio: a phone photo of three drawn screens turned into a page](docs/screenshots/preview.jpg)

| Arrows become links (F2) | Accessibility score and auto-fix (F5) |
|---|---|
| ![Flow map](docs/screenshots/flow-map.jpg) | ![Accessibility](docs/screenshots/accessibility.jpg) |

## How it works

```
photo ─► preprocess (shadows, tilt) ─► YOLO boxes ─► OCR text ─► layout + arrows + notes
      ─► UIDocument JSON (shared/component.schema.json) ─► LLM refine (or rules offline)
      ─► HTML / React / full stack ─► axe-core fix loop ─► preview, QR, zip
```

Everything after the JSON reads only the JSON, so the same document feeds every output and Restruct Warp.
Diagrams: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Results: [docs/results/RESULTS.md](docs/results/RESULTS.md).

## Stack (all free / open source)

FastAPI · async SQLAlchemy · SQLite · JWT + bcrypt · OpenCV · Ultralytics YOLOv8 · PaddleOCR ·
OpenAI-compatible LLM (Groq free tier or local Ollama) · axe-core · React · Vite · Tailwind · Monaco

> YOLOv8 (Ultralytics) is AGPL-3.0: if you deploy it publicly, publish this repository's source too,
> or swap in an Apache-licensed detector such as RT-DETR.

## Run it locally

Needs Python 3.11 and Node 20.

```powershell
# backend
cd backend
py -3.11 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt -r requirements-vision.txt
copy ..\.env.example .env        # then set JWT_SECRET (and LLM_API_KEY for Groq)
cd a11y; npm install; cd ..
uvicorn app.main:app --reload    # http://localhost:8000/docs

# frontend (second terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

The detector needs trained weights at `backend/weights/sketch_yolo.pt` (next section).
Without an LLM key, refinement and accessibility fixes use built-in rules.

## Train the detector

```powershell
python ml/synth_sketches.py --n 600 --out datasets/synthetic           # synthetic sketches + YOLO labels
python ml/train_yolo.py --data datasets/synthetic/data.yaml --epochs 100 # Kaggle GPU; add --device cpu locally
```

Add real photos labelled in Label Studio (export as YOLO) to the same folders for better accuracy.
Classes: `shared/detector_classes.json`.

## Evaluate

```powershell
python ml/evaluate.py --json results.json               # precision, recall, component accuracy, layout IoU, links, notes
python ml/evaluate.py --photo                           # inputs tilted, shaded, blurred like phone photos
python ml/evaluate.py --ocr --limit 30                  # also score the text and notes OCR read (slow on CPU)
python ml/evaluate.py --no-preprocess                   # ablation
python ml/baseline_vlm.py --limit 30                    # vision-LLM-only baseline
python ml/inspect_pipeline.py --n 10                    # JSON + annotated image per sketch, to eyeball mistakes
```

## Tests

```powershell
cd backend
python -m pytest
```

## Open in Restruct Warp

Copy `integration/restruct_warp/sketch_import.py` into Restruct Warp and set `VITE_RESTRUCT_URL` in
`frontend/.env.local`; the Studio then shows an **Open in Restruct Warp** button. Details in
[docs/INTEGRATION.md](docs/INTEGRATION.md).

## Deploy (free)

Live site: **https://sketch2ui-lac.vercel.app** (Vercel). The API runs in Google Colab behind a Cloudflare tunnel:
open `deploy/colab_backend.ipynb`, *Run all*, and use the link it prints. Details: [docs/DEPLOY.md](docs/DEPLOY.md).

## Project layout

```
backend/app/       FastAPI app: models, routers, schemas, security, services (vision, codegen, a11y …)
backend/a11y/      axe-core runner (Node)
backend/tests/     pytest suite
frontend/          Sketch Studio (React)
ml/                synthetic data, training, evaluation, baseline
shared/            component.schema.json, detector classes, examples
integration/       drop-in router for Restruct Warp
docs/              architecture, results, integration notes
```
