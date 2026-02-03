from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

import asyncpg
import logging

from sqlalchemy import text

from mqttap.db.schema import metadata
from mqttap.config import settings
from mqttap.security import hash_password

logger = logging.getLogger(__name__)

async def ensure_database_exists() -> None:
    url = make_url(settings.database_dsn)
    database = url.database
    if not database:
        return

    if settings.admin_database_dsn:
        admin_url = make_url(settings.admin_database_dsn)
    else:
        admin_url = url.set(database="postgres")

    admin_url = admin_url.set(drivername="postgresql")
    logger.info(
        "Ensuring database exists: %s",
        admin_url.render_as_string(hide_password=True),
    )
    conn = await asyncpg.connect(admin_url.render_as_string(hide_password=False))
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database,
        )
        if not exists:
            logger.info("Creating database %s", database)
            await conn.execute(f'CREATE DATABASE "{database}"')
        else:
            logger.info("Database %s already exists", database)
    finally:
        await conn.close()


async def init_base_schema(engine: AsyncEngine) -> None:
    await ensure_database_exists()
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        await _seed_roles_and_admin(conn)


async def _seed_roles_and_admin(conn) -> None:
    await conn.execute(
        text(
            """
            INSERT INTO roles (id, name) VALUES (1, 'admin')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    await conn.execute(
        text(
            """
            INSERT INTO roles (id, name) VALUES (2, 'user')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    if settings.admin_email and settings.admin_password:
        password_hash = hash_password(settings.admin_password)
        await conn.execute(
            text(
                """
                INSERT INTO users (email, password_hash, role_id)
                VALUES (:email, :password_hash, 1)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {"email": settings.admin_email, "password_hash": password_hash},
        )
