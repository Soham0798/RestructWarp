"""Request/response models for /projects and /sketch."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.component_schema import UIDocument


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SketchSummary(BaseModel):
    id: int
    status: str
    created_at: datetime
    a11y_before: Optional[int] = None
    a11y_after: Optional[int] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    sketches: list[SketchSummary] = []


class AnalyzeOut(BaseModel):
    sketch_id: int
    status: str
    refined_by: str           # 'vision', 'llm' or 'rules'
    document: UIDocument


class GenerateOut(BaseModel):
    sketch_id: int
    pages: dict[str, str]     # file name -> html
    a11y_before: Optional[int]
    a11y_after: Optional[int]
    a11y_fixed_by: str        # 'llm', 'rules', 'none' or 'unavailable'
    preview_url: str          # open on a phone via QR code
