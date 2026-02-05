"""Database connection and session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.logging_config import get_logger
from app.settings import settings
from app.storage.models import Base

logger = get_logger(__name__)


class Database:
    """Database connection manager."""

    def __init__(self, database_url: str | None = None):
        """Initialize database connection.

        Args:
            database_url: Database URL (defaults to settings)
        """
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(
            self.database_url,
            echo=settings.env == "development",
            pool_pre_ping=True,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=self.engine,
        )
        logger.info("database_initialized", url=self.database_url)

    def create_tables(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("tables_created")

    def drop_tables(self) -> None:
        """Drop all tables from the database."""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("tables_dropped")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations.

        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database instance
db = Database()
