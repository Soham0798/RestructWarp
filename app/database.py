from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


def _prepare_database_url(url: str) -> tuple[str, dict]:
    """Returns (url, connect_args) that work with SQLAlchemy's async engine.

    Local dev uses SQLite. Hosted Postgres providers (Neon, Render, ...) hand out
    `postgres://...?sslmode=require` URLs, which need the asyncpg driver and its
    own way of asking for SSL.
    """
    if url.startswith("sqlite"):
        # SQLite needs check_same_thread=False
        return url, {"check_same_thread": False}

    parts = urlsplit(url)
    if parts.scheme in ("postgres", "postgresql"):
        query = dict(parse_qsl(parts.query))
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)  # libpq-only option asyncpg rejects
        connect_args = {"ssl": True} if sslmode and sslmode != "disable" else {}
        url = urlunsplit(parts._replace(scheme="postgresql+asyncpg", query=urlencode(query)))
        return url, connect_args

    return url, {}


_database_url, _connect_args = _prepare_database_url(settings.DATABASE_URL)

engine = create_async_engine(
    _database_url,
    echo=False,
    connect_args=_connect_args,
    pool_pre_ping=True,  # hosted databases drop idle connections
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
