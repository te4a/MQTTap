from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from mqttap.config import settings


def create_engine_from_settings() -> AsyncEngine:
    url = make_url(settings.database_dsn)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+asyncpg")
    return create_async_engine(url, pool_pre_ping=True)


engine = create_engine_from_settings()
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
