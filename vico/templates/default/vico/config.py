import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.warning(
            "DATABASE_URL not configured. "
            "Using SQLite for development. "
            "Configure DATABASE_URL before production."
        )
        return "sqlite:///./vico.db"

    return database_url