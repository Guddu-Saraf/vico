import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

def _get_int_env(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"Environment variable {name}={raw!r} is not a valid integer."
        )


POOL_SIZE = _get_int_env("POOL_SIZE", "5")
MAX_OVERFLOW = _get_int_env("MAX_OVERFLOW", "10")
POOL_TIMEOUT = _get_int_env("POOL_TIMEOUT", "30")
POOL_RECYCLE = _get_int_env("POOL_RECYCLE", "1800")


if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./vico.db"
    logger.warning(
        "DATABASE_URL not configured. Using SQLite for development. "
        "Configure DATABASE_URL before production."
    )


is_sqlite = DATABASE_URL.startswith("sqlite")


engine_kwargs = {}

if not is_sqlite:
    engine_kwargs.update(
        {
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT,
            "pool_recycle": POOL_RECYCLE,
            # Without this, a connection silently closed by the DB server
            # or an intermediate proxy/load balancer surfaces as an
            # OperationalError on the next request instead of being
            # transparently replaced.
            "pool_pre_ping": True,
        }
    )
else:
    engine_kwargs["connect_args"] = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    **engine_kwargs,
)


# `autocommit` is intentionally omitted: it's the default under
# SQLAlchemy 1.4 and was removed entirely from Session/sessionmaker in
# SQLAlchemy 2.0, where passing it raises at import time. Leaving it
# out is a no-op on 1.4 and avoids a hard break if/when you upgrade.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
)


def get_db():
    """
    FastAPI-style DB session dependency.

    Commits on a clean exit, rolls back and re-raises on any exception,
    and always closes the session. This assumes callers do NOT already
    call db.commit() themselves — if your route/service layer already
    manages commits explicitly, remove the commit() call here to avoid
    double-committing.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()