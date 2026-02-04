import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from mqttap.config import settings as env_settings

logger = logging.getLogger(__name__)


DEFAULTS: dict[str, Any] = {
    "mqtt_host": env_settings.mqtt_host,
    "mqtt_port": env_settings.mqtt_port,
    "mqtt_topics": env_settings.mqtt_topics,
    "mqtt_username": env_settings.mqtt_username,
    "mqtt_password": env_settings.mqtt_password,
    "float_precision": env_settings.float_precision,
    "default_agg": env_settings.default_agg,
    "default_interval": env_settings.default_interval,
}


def _parse_value(value: str, value_type: str) -> Any:
    if value_type == "int":
        try:
            return int(value)
        except ValueError:
            return 0
    if value_type == "bool":
        return value.lower() in ("1", "true", "yes", "on")
    return value


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    return "string"


async def seed_settings_if_empty(conn) -> None:
    count = await conn.execute(text("SELECT COUNT(*) FROM settings"))
    if count.scalar_one() != 0:
        return
    for key, value in DEFAULTS.items():
        if value is None:
            continue
        await conn.execute(
            text(
                """
                INSERT INTO settings (key, value, type)
                VALUES (:key, :value, :type)
                """
            ),
            {"key": key, "value": str(value), "type": _infer_type(value)},
        )


async def load_settings(engine: AsyncEngine) -> dict[str, Any]:
    sql = text("SELECT key, value, type FROM settings")
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()
    values: dict[str, Any] = {}
    for row in rows:
        values[row["key"]] = _parse_value(row["value"], row["type"])
    merged = {**DEFAULTS, **values}
    return merged


async def save_settings(engine: AsyncEngine, payload: dict[str, Any]) -> None:
    sql = text(
        """
        INSERT INTO settings (key, value, type)
        VALUES (:key, :value, :type)
        ON CONFLICT (key) DO UPDATE SET value = :value, type = :type, updated_at = now()
        """
    )
    async with engine.begin() as conn:
        for key, value in payload.items():
            await conn.execute(
                sql,
                {"key": key, "value": "" if value is None else str(value), "type": _infer_type(value)},
            )
