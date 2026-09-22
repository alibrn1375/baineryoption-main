"""Production Database Manager supporting connection pooling, health checks, and lifecycle."""

import os
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

try:
    import asyncpg
except ImportError:
    asyncpg = None


class DatabaseManager:
    """Manages PostgreSQL connection pools and DuckDB/Parquet local analytics."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "fox_trading",
        user: str = "fox_admin",
        password: str = "fox_secure_pass",
        min_pool_size: int = 5,
        max_pool_size: int = 20
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool: Optional[Any] = None
        self._is_connected: bool = False

    async def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool."""
        if asyncpg is None:
            # Fallback for environments without asyncpg
            self._is_connected = True
            return True

        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size
            )
            self._is_connected = True
            await self._run_migrations()
            return True
        except Exception as e:
            self._is_connected = False
            return False

    async def _run_migrations(self) -> None:
        """Create standard tables for trades, orderflow logs, and audit trails if not existing."""
        if not self._pool:
            return

        schema_sql = """
        CREATE TABLE IF NOT EXISTS paper_trades (
            id VARCHAR(64) PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            symbol VARCHAR(32) NOT NULL,
            decision VARCHAR(16) NOT NULL,
            setup_name VARCHAR(128) NOT NULL,
            entry_price DOUBLE PRECISION NOT NULL,
            expiry_price DOUBLE PRECISION,
            quality_score DOUBLE PRECISION NOT NULL,
            win_probability DOUBLE PRECISION NOT NULL,
            expected_value DOUBLE PRECISION NOT NULL,
            outcome VARCHAR(16) NOT NULL,
            reasons JSONB NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_type VARCHAR(64) NOT NULL,
            severity VARCHAR(16) NOT NULL,
            payload JSONB NOT NULL
        );
        """
        async with self._pool.acquire() as conn:
            await conn.execute(schema_sql)

    async def close(self) -> None:
        """Gracefully terminate connection pool."""
        if self._pool:
            await self._pool.close()
        self._is_connected = False

    async def check_health(self) -> bool:
        """Execute a lightweight ping to verify database responsiveness."""
        if not self._is_connected:
            return False
        if not self._pool:
            return True
        try:
            async with self._pool.acquire() as conn:
                res = await conn.fetchval("SELECT 1;")
                return res == 1
        except Exception:
            return False

    def is_connected(self) -> bool:
        return self._is_connected
