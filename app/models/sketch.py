"""One uploaded sketch and everything generated from it."""
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow

# uploaded -> analyzed (component JSON ready) -> generated (code ready); failed at any point
SKETCH_STATUSES = ("uploaded", "analyzed", "generated", "failed")


class Sketch(Base):
    __tablename__ = "sketches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    ui_json: Mapped[Optional[str]] = mapped_column(Text)  # UIDocument (shared/component.schema.json)
    code_html: Mapped[Optional[str]] = mapped_column(Text)  # JSON {page file: html}
    preview_token: Mapped[str] = mapped_column(String(32), unique=True, index=True,
                                               default=lambda: secrets.token_urlsafe(16))  # QR preview link
    a11y_before: Mapped[Optional[int]] = mapped_column(Integer)  # accessibility score, 0-100
    a11y_after: Mapped[Optional[int]] = mapped_column(Integer)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="sketches")
