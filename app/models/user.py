from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    credits = Column(Integer, default=10)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Sketch Studio projects; deleting a user removes their projects and sketches
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
