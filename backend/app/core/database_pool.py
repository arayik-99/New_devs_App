import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

logger = logging.getLogger(__name__)


def _async_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


class DatabasePool:
    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection pool. Idempotent - safe to call per request."""
        if self.session_factory is not None:
            return

        try:
            database_url = _async_database_url(settings.database_url)

            self.engine = create_async_engine(
                database_url,
                pool_size=settings.database_pool_size,  # Number of connections to maintain
                max_overflow=settings.database_max_overflow,  # Additional connections when needed
                pool_timeout=settings.database_pool_timeout,  # Wait time for a free connection
                pool_pre_ping=True,  # Validate connections
                pool_recycle=settings.database_pool_recycle,  # Recycle connections periodically
                echo=False  # Set to True for SQL debugging
            )

            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            logger.info("✅ Database connection pool initialized")

        except Exception as e:
            logger.error(f"❌ Database pool initialization failed: {e}")
            self.engine = None
            self.session_factory = None
            raise

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """Get a database session from the pool, released back on exit."""
        if not self.session_factory:
            raise RuntimeError("Database pool not initialized")
        async with self.session_factory() as session:
            yield session

# Global database pool instance
db_pool = DatabasePool()

async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency to get database session"""
    await db_pool.initialize()
    async with db_pool.get_session() as session:
        yield session
