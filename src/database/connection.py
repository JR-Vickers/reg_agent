"""Database connection management."""

import asyncpg
from typing import Optional
import logging
from contextlib import asynccontextmanager

from src.config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """Async PostgreSQL database connection manager."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create database connection pool."""
        try:
            # Parse database URL to handle password placeholder
            db_url = settings.database_url
            if "[password]" in db_url:
                logger.warning(
                    "Database URL contains [password] placeholder. "
                    "Please set the actual password in your environment."
                )
                return

            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=1,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'reg-agent',
                    'timezone': 'UTC'
                }
            )
            logger.info("Database connection pool created")

        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        async with self.pool.acquire() as conn:
            yield conn

    async def execute_schema(self, schema_path: str = "src/database/schema.sql") -> None:
        """Execute database schema from SQL file."""
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()

            async with self.acquire() as conn:
                await conn.execute(schema_sql)
                logger.info("Database schema executed successfully")

        except FileNotFoundError:
            logger.error(f"Schema file not found: {schema_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to execute schema: {e}")
            raise


# Global database instance
db = Database()


async def get_database() -> Database:
    """Get database instance (dependency injection)."""
    return db


async def init_database() -> None:
    """Initialize database connection (optional - Supabase REST client is primary)."""
    try:
        await db.connect()
        if settings.env != "production":
            try:
                await db.execute_schema()
            except Exception as e:
                logger.warning(f"Schema execution skipped: {e}")
    except Exception as e:
        logger.warning(f"Direct database connection unavailable (using Supabase REST): {e}")


async def close_database() -> None:
    """Close database connections."""
    await db.disconnect()