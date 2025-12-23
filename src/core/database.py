"""
Database management for ConnectifyVPN Premium Suite
"""

import os
import asyncio
import datetime
from pathlib import Path
from typing import Optional, AsyncGenerator, Any, Dict, List, Union

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import Settings
from .models import Base


class DatabaseManager:
    """
    Manages PostgreSQL and Redis connections with connection pooling
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.redis_client: Optional[Redis] = None

    async def initialize(self):
        """Initialize database connections"""
        await self._init_postgres()
        await self._init_redis()

    async def _init_postgres(self):
        """Initialize PostgreSQL connection pool"""
        self.engine = create_async_engine(
            self.settings.database.dsn,
            echo=self.settings.server.debug,
            pool_size=self.settings.database.pool_size,
            max_overflow=self.settings.database.max_overflow,
            pool_pre_ping=True,
            pool_recycle=300,
            future=True,
        )

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        # Test connection (SQLAlchemy 2.0 needs text())
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

    async def _init_redis(self):
        """Initialize Redis connection"""
        self.redis_client = Redis.from_url(
            self.settings.redis.url,
            max_connections=self.settings.redis.max_connections,
            decode_responses=True,
        )
        await self.redis_client.ping()

    async def create_tables(self):
        """Create all database tables"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        if not self.session_factory:
            raise RuntimeError("Session factory not initialized")
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_redis(self) -> Redis:
        """Get Redis client"""
        if not self.redis_client:
            raise RuntimeError("Redis not initialized")
        return self.redis_client

    async def health_check(self) -> Dict[str, bool]:
        """Check database health"""
        health = {"postgres": False, "redis": False}

        # PostgreSQL
        try:
            if self.engine:
                async with self.engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                health["postgres"] = True
        except Exception:
            pass

        # Redis
        try:
            if self.redis_client:
                await self.redis_client.ping()
                health["redis"] = True
        except Exception:
            pass

        return health

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        stats: Dict[str, Any] = {}

        async with self.engine.begin() as conn:
            # DB size
            result = await conn.execute(text("SELECT pg_database_size(current_database())"))
            stats["postgres_size_bytes"] = result.scalar()

            # Connections count
            result = await conn.execute(text("SELECT count(*) FROM pg_stat_activity"))
            stats["postgres_connections"] = result.scalar()

        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats["redis_memory"] = redis_info.get("used_memory_human", "N/A")
                stats["redis_connected_clients"] = redis_info.get("connected_clients", 0)
                stats["redis_total_commands_processed"] = redis_info.get(
                    "total_commands_processed", 0
                )
            except Exception:
                pass

        return stats

    async def close(self):
        """Close all database connections"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None

        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    async def execute_raw_query(
        self,
        query: Union[str, Any],
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query safely.
        - Accepts string SQL or a SQLAlchemy text()/select() object.
        """
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        stmt = text(query) if isinstance(query, str) else query

        async with self.engine.connect() as conn:
            result = await conn.execute(stmt, params or {})
            # result.mappings() returns dict-like rows
            return [dict(row) for row in result.mappings().all()]

    async def backup_database(self, backup_path: str) -> str:
        """Create database backup using pg_dump (custom format)"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"connectifyvpn_backup_{timestamp}.dump"
        filepath = Path(backup_path) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "pg_dump",
            "-h",
            self.settings.database.host,
            "-p",
            str(self.settings.database.port),
            "-U",
            self.settings.database.user,
            "-d",
            self.settings.database.name,
            "-f",
            str(filepath),
            "--format=custom",
            "--verbose",
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = self.settings.database.password

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Backup failed: {stderr.decode(errors='ignore')}")

        return str(filepath)

    async def restore_database(self, backup_path: str) -> bool:
        """Restore database from pg_dump custom backup using pg_restore"""
        cmd = [
            "pg_restore",
            "-h",
            self.settings.database.host,
            "-p",
            str(self.settings.database.port),
            "-U",
            self.settings.database.user,
            "-d",
            self.settings.database.name,
            "-c",  # clean before restore
            "--verbose",
            backup_path,
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = self.settings.database.password

        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Restore failed: {stderr.decode(errors='ignore')}")

        return True


class DatabaseUtils:
    """Utility functions for database operations"""

    @staticmethod
    async def create_index(
        db: DatabaseManager, table: str, columns: List[str], unique: bool = False
    ):
        """Create database index"""
        if not db.engine:
            raise RuntimeError("Database engine not initialized")

        index_name = f"idx_{table}_{'_'.join(columns)}"
        cols = ", ".join([f'"{c}"' for c in columns])

        if unique:
            query = f'CREATE UNIQUE INDEX IF NOT EXISTS "{index_name}" ON "{table}" ({cols})'
        else:
            query = f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table}" ({cols})'

        async with db.engine.begin() as conn:
            await conn.execute(text(query))

    @staticmethod
    async def table_exists(db: DatabaseManager, table: str) -> bool:
        """Check if table exists"""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table
        ) AS exists
        """
        result = await db.execute_raw_query(query, {"table": table})
        return bool(result[0]["exists"]) if result else False

    @staticmethod
    async def get_table_size(db: DatabaseManager, table: str) -> int:
        """Get table size in bytes"""
        # pg_total_relation_size needs regclass; safest build with quotes
        query = f'SELECT pg_total_relation_size(\'"{table}"\') AS size'
        result = await db.execute_raw_query(query)
        return int(result[0]["size"]) if result else 0

    @staticmethod
    async def vacuum_analyze(db: DatabaseManager, table: Optional[str] = None):
        """
        Run VACUUM ANALYZE.
        IMPORTANT: VACUUM cannot run inside a transaction, so use AUTOCOMMIT.
        """
        if not db.engine:
            raise RuntimeError("Database engine not initialized")

        base = "VACUUM (ANALYZE)"
        query = f"{base} {table}" if table else base

        async with db.engine.connect() as conn:
            # autocommit for VACUUM
            await conn.execution_options(isolation_level="AUTOCOMMIT").execute(text(query))
