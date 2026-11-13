"""/sketch: upload -> analyze -> edit -> generate -> export, plus the public /preview link."""
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, Sketch, User
from app.routers.projects import owned_project
from app.schemas.component_schema import UIDocument
from app.schemas.sketch_schema import AnalyzeOut, GenerateOut
from app.security.deps import get_current_user
from app.services import (a11y_service, codegen_service, fullstack_service, react_export, refine_service,
                          sketch_reader, vision_ai)

router = APIRouter(tags=["sketch"])

UPLOADS = Path(__file__).resolve().parents[2] / "uploads"
ALLOWED = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_BYTES = 10 * 1024 * 1024


class NoDetector(RuntimeError):
    """The optional YOLO detector isn't installed (requirements-vision.txt) or has no trained weights."""


def detect_layout(data: bytes, name: str) -> UIDocument:
    """Runs Sketch2UI's detector + OCR pipeline. Imported here because it needs heavy vision packages."""
    try:
        from app.services import pipeline
        from app.services.vision.detect import DetectorUnavailable
    except ImportError as e:
        raise NoDetector(str(e)) from e
    try:
        return pipeline.analyze(data, name)
    except DetectorUnavailable as e:
        raise NoDetector(str(e)) from e


async def owned_sketch(sketch_id: int, user: User, db: AsyncSession) -> Sketch:
    sketch = await db.scalar(select(Sketch).join(Project)
                             .where(Sketch.id == sketch_id, Project.user_id == user.id))
    if not sketch:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sketch not found")
    return sketch


@router.post("/sketch/analyze", response_model=AnalyzeOut, status_code=status.HTTP_201_CREATED)
async def analyze(project_id: int = Form(...), file: UploadFile = File(...),
                  user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = await owned_project(project_id, user, db)
    if file.content_type not in ALLOWED:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a PNG, JPG or WEBP image")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image must be under 10 MB")

    UPLOADS.mkdir(exist_ok=True)
    path = UPLOADS / f"{uuid.uuid4().hex}{ALLOWED[file.content_type]}"  # random name: no overwrites
    path.write_bytes(data)
    sketch = Sketch(project_id=project.id, image_path=path.name)  # stored under UPLOADS
    db.add(sketch)
    await db.commit()

    detected = True
    try:
        doc = await run_in_threadpool(detect_layout, data, project.name)  # CPU-heavy: keep the server responsive
    except ValueError as e:
        sketch.status, sketch.error = "failed", str(e)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    except NoDetector:
        detected, doc = False, sketch_reader.blank_document(project.name)

    # Claude reads the sketch (with the detector's screens and arrows when there is one); failing that,
    # Sketch2UI's own vision model, and failing that the LLM/rules tidy the detector's tree
    read = await sketch_reader.describe(data, file.content_type, doc) or await vision_ai.describe(data, doc)
    if read:
        doc, how = read, "vision"
    elif detected:
        doc, how = await refine_service.refine(doc)
    else:
        sketch.status, sketch.error = "failed", "No sketch reader available"
        await db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The sketch could not be read. Check ANTHROPIC_API_KEY, or install the detector.")
    sketch.ui_json, sketch.status = doc.model_dump_json(exclude_none=True), "analyzed"
    await db.commit()
    return AnalyzeOut(sketch_id=sketch.id, status=sketch.status, refined_by=how, document=doc)


@router.get("/sketch/{sketch_id}", response_model=UIDocument)
async def get_document(sketch_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sketch = await owned_sketch(sketch_id, user, db)
    if not sketch.ui_json:
        raise HTTPException(status.HTTP_409_CONFLICT, "This sketch has not been analyzed")
    return UIDocument.model_validate_json(sketch.ui_json)


@router.put("/sketch/{sketch_id}/json", response_model=UIDocument)
async def save_document(sketch_id: int, doc: UIDocument, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """Save the user's edits from the JSON / visual editor (validated by the schema)."""
    sketch = await owned_sketch(sketch_id, user, db)
    sketch.ui_json, sketch.status, sketch.code_html = doc.model_dump_json(exclude_none=True), "analyzed", None
    await db.commit()
    return doc


@router.post("/sketch/{sketch_id}/generate", response_model=GenerateOut)
async def generate(sketch_id: int, request: Request, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    sketch = await owned_sketch(sketch_id, user, db)
    doc = UIDocument.model_validate_json(await get_document_json(sketch))
    pages, before, after, how = codegen_service.render_site(doc), [], [], "none"
    try:
        for name, html in pages.items():
            result = await a11y_service.improve(html)
            pages[name] = result["html"]
            before.append(result["before"])
            after.append(result["after"])
            how = result["how"] if result["how"] != "none" else how
    except a11y_service.AuditUnavailable:
        how = "unavailable"
    sketch.code_html, sketch.status = json.dumps(pages), "generated"
    sketch.a11y_before = min(before) if before else None
    sketch.a11y_after = min(after) if after else None
    await db.commit()
    return GenerateOut(sketch_id=sketch.id, pages=pages, a11y_before=sketch.a11y_before,
                       a11y_after=sketch.a11y_after, a11y_fixed_by=how,
                       preview_url=str(request.url_for("preview", token=sketch.preview_token, page="index.html")))


async def get_document_json(sketch: Sketch) -> str:
    if not sketch.ui_json:
        raise HTTPException(status.HTTP_409_CONFLICT, "This sketch has not been analyzed")
    return sketch.ui_json


@router.get("/sketch/{sketch_id}/export")
async def export(sketch_id: int, target: str = Query("html", pattern="^(html|react|fullstack)$"),
                 user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    sketch = await owned_sketch(sketch_id, user, db)
    doc = UIDocument.model_validate_json(await get_document_json(sketch))
    if target == "react":
        files = react_export.build_project(doc)
    elif target == "fullstack":
        files = fullstack_service.build_fullstack(doc)
    else:
        files = json.loads(sketch.code_html) if sketch.code_html else codegen_service.render_site(doc)
    return Response(react_export.to_zip(files), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="sketch-{sketch.id}-{target}.zip"'})


@router.get("/preview/{token}/{page}", response_class=HTMLResponse, name="preview")
async def preview(token: str, page: str, db: AsyncSession = Depends(get_db)):
    """Public, unguessable link so a phone can open the page by scanning a QR code (F1)."""
    sketch = await db.scalar(select(Sketch).where(Sketch.preview_token == token))
    pages = json.loads(sketch.code_html) if sketch and sketch.code_html else {}
    if page not in pages:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preview not found")
    return HTMLResponse(pages[page])
