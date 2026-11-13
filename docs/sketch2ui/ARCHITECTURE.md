# Architecture

GitHub draws the diagrams below. For the report, paste a block into https://mermaid.live and export PNG/SVG.

## Request flow

```mermaid
flowchart LR
    U([User: photo of a sketch]) --> FE[Sketch Studio<br/>React + Vite]
    FE -- "POST /sketch/analyze" --> API[FastAPI backend]

    subgraph Vision["Vision pipeline (backend/app/services/vision)"]
        P[preprocess<br/>resize · shadows · deskew] --> D[detect<br/>YOLOv8n, 14 classes]
        D --> O[ocr<br/>PaddleOCR, word-level]
        O --> L[layout<br/>screens · nesting · rows · forms]
        L --> F[flow<br/>arrows → links F2]
        L --> N[notes<br/>notes → styleHints F3]
    end

    API --> P
    F & N --> J[(UIDocument JSON<br/>shared/component.schema.json)]
    J --> R[refine<br/>LLM or rules]
    R --> C[codegen<br/>HTML + Tailwind, one page per screen]
    C --> A[a11y<br/>axe-core score → fix → re-score F5]
    A --> FE

    J --> X1[React / Vite zip F1]
    J --> X2[Full-stack zip<br/>FastAPI + SQLite per form F4]
    C --> Q[Public preview + QR F1]
    J -. "Open in Restruct Warp" .-> RW[Restruct Warp<br/>POST /generate/import]

    API --- DB[(SQLite<br/>users · projects · sketches)]
```

Everything after the JSON reads only the JSON. The detector, OCR or LLM can be swapped without
touching code generation, and Restruct Warp can use the same document.

## Data model

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : owns
    PROJECTS ||--o{ SKETCHES : has
    USERS {
        int id
        string email
        string password "bcrypt hash"
        int credits
        string role
    }
    PROJECTS {
        int id
        int user_id
        string name
    }
    SKETCHES {
        int id
        int project_id
        string status "uploaded, analyzed, generated, failed"
        json ui_json "UIDocument"
        json code_html "page name to HTML"
        string preview_token "public preview / QR"
        int a11y_before
        int a11y_after
    }
```

The `users` table has the same columns as Restruct Warp's, so one account works in both apps once they share it.

## Training and evaluation

```mermaid
flowchart LR
    S[ml/synth_sketches.py<br/>boxes + words answer key] --> T[ml/train_yolo.py<br/>Kaggle T4 GPU]
    T --> W[(backend/weights/sketch_yolo.pt)]
    W --> E[ml/evaluate.py<br/>--photo --ocr --no-preprocess]
    W --> I[ml/inspect_pipeline.py<br/>JSON + annotated image]
    E --> RES[docs/results]
```
