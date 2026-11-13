# Merging Sketch2UI into Restruct Warp

Sketch2UI was built to slot into Restruct Warp (reconstruct-wrap). Both use FastAPI, async SQLAlchemy,
SQLite and the same JWT login, so most of it is copy and register.

## What is already shared

| Piece | Sketch2UI | Restruct Warp | Status |
|---|---|---|---|
| Users table | `users` (email, password hash, credits, role, created_at) | same columns | Same table: accounts work in both |
| Login token | HS256 JWT with `user_id`, `role`, 12 h | same | Same `JWT_SECRET` → one login for both |
| Auth routes | `/auth/register`, `/auth/login` | same | Keep Restruct Warp's; drop ours |
| LLM | `openai` SDK with `LLM_BASE_URL` (Groq or Ollama) | Groq SDK | Either works; ours also runs offline |
| Page format | `shared/component.schema.json` (UIDocument v2) | raw HTML per generation | **Adopt the schema** (below) |

## Steps

1. **Copy the services**: `backend/app/services/` (vision, pipeline, refine, codegen, react_export,
   fullstack, a11y) and `backend/a11y/` into reconstruct-wrap's `app/services/`.
2. **Copy the models**: `Project` and `Sketch` (`app/models/project.py`, `sketch.py`). They point at the
   same `users.id`, so no data migration is needed for users.
3. **Register the routers** in Restruct Warp's `main.py`:
   ```python
   from app.routers import projects, sketch
   app.include_router(projects.router)
   app.include_router(sketch.router)
   ```
4. **Settings**: add `LLM_BASE_URL`, `LLM_CODE_MODEL`, `LLM_VISION_MODEL`, `FRONTEND_URL` to its
   `config.py`, and put `backend/weights/sketch_yolo.pt` in place.
5. **Use one page format**: have Restruct Warp's editor load and save `UIDocument` JSON
   (`app/schemas/component_schema.py`) instead of raw HTML, and render it with `codegen_service.render_site`.
   Then a sketch opens as an editable page, and every page gets the HTML/React/full-stack exports.
6. **"Open in Restruct Warp"** (works before the full merge):
   - Copy `integration/restruct_warp/sketch_import.py` to reconstruct-wrap's `app/routers/` and
     `app.include_router(sketch_import.router)` in its `main.py`. It adds `POST /generate/import`.
   - Set `VITE_RESTRUCT_URL` in Sketch2UI's `frontend/.env.local`; the Studio then shows the button.
   - The button sends the first page's HTML plus the UIDocument. Restruct Warp saves it as a normal
     "website" generation (no credit spent), so it appears in `/dashboard/history`. The JSON is kept
     inside the HTML as `<script type="application/json" id="sketch2ui-document">` so the editor can
     read it back without a new column.
   - The login must exist in Restruct Warp: share `JWT_SECRET` and point both apps at the same users
     table (Steps 2 and 4), otherwise it answers 401.

## Things to fix in reconstruct-wrap while merging

- CORS is `*`: use the `FRONTEND_URL` list like Sketch2UI.
- `emergent_ai.db` and `__pycache__` are committed: remove them and add a `.gitignore`.
- `/generate/status` uses `settings` without importing it.
- `claude-3-5-sonnet-20241022` is retired: point the fallback at a current model.
- `@app.on_event("startup")` is deprecated: use `lifespan` as in Sketch2UI.
