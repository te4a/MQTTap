import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


_ident_re = re.compile(r"[^a-zA-Z0-9_]+")


def _sanitize_identifier(value: str, prefix: str) -> str:
    value = str(value)
    cleaned = _ident_re.sub("_", value.strip().lower()).strip("_")
    if not cleaned:
        cleaned = prefix
    if cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return cleaned[:63]


def topic_to_table(topic: str, is_json: bool) -> str:
    if is_json:
        return _sanitize_identifier(topic, "topic")
    last = topic.split("/")[-1]
    return _sanitize_identifier(last, "topic")


def json_key_to_column(key: str) -> str:
    return _sanitize_identifier(key, "field")


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


@dataclass
class ColumnSpec:
    name: str
    type_name: str


def _infer_type(value: Any) -> str:
    if value is None:
        return "text"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "bigint"
    if isinstance(value, float):
        return "double precision"
    if isinstance(value, str):
        return "text"
    return "jsonb"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def _is_integer_float(value: float) -> bool:
    return value.is_integer()


def _widen_type(current: str, incoming: str) -> str | None:
    current = current.lower()
    incoming = incoming.lower()
    if current == incoming:
        return None
    numeric = {"bigint", "double precision"}
    if current in numeric and incoming in numeric:
        if current == "bigint" and incoming == "double precision":
            return "double precision"
        return None
    if current == "boolean" and incoming == "text":
        return "text"
    if current == "text":
        return None
    return "text"


async def ensure_topic_table(engine: AsyncEngine, table_name: str, is_json: bool) -> None:
    quoted = quote_ident(table_name)
    if is_json:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {quoted} (
            id BIGSERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    else:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {quoted} (
            id BIGSERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            value_type TEXT NOT NULL,
            value_int BIGINT,
            value_float DOUBLE PRECISION,
            value_bool BOOLEAN,
            value_text TEXT,
            value_json JSONB
        )
        """
    async with engine.begin() as conn:
        await conn.execute(text(ddl))


async def get_table_columns(engine: AsyncEngine, table_name: str) -> dict[str, str]:
    sql = text(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = :table_name
        """
    )
    async with engine.begin() as conn:
        rows = await conn.execute(sql, {"table_name": table_name})
    return {row[0]: row[1] for row in rows.fetchall()}


async def ensure_columns(
    engine: AsyncEngine, table_name: str, columns: list[ColumnSpec]
) -> dict[str, str]:
    existing = await get_table_columns(engine, table_name)
    quoted_table = quote_ident(table_name)
    async with engine.begin() as conn:
        for col in columns:
            if col.name in existing:
                continue
            ddl = f"ALTER TABLE {quoted_table} ADD COLUMN {quote_ident(col.name)} {col.type_name}"
            await conn.execute(text(ddl))
            existing[col.name] = col.type_name
    return existing


async def widen_column(
    engine: AsyncEngine, table_name: str, column: str, new_type: str
) -> None:
    quoted_table = quote_ident(table_name)
    quoted_col = quote_ident(column)
    ddl = f"""
    ALTER TABLE {quoted_table}
    ALTER COLUMN {quoted_col}
    TYPE {new_type}
    USING {quoted_col}::{new_type}
    """
    async with engine.begin() as conn:
        await conn.execute(text(ddl))


def normalize_value_for_column(value: Any, column_type: str) -> Any:
    if value is None:
        return None
    column_type = column_type.lower()
    if column_type == "bigint":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, float) and _is_integer_float(value):
            return int(value)
        if isinstance(value, int):
            return value
    if column_type == "double precision":
        if isinstance(value, (int, float, bool)):
            return float(value)
    if column_type == "boolean":
        if isinstance(value, bool):
            return value
    if column_type == "jsonb":
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def infer_column_spec(name: str, value: Any) -> ColumnSpec:
    return ColumnSpec(name=name, type_name=_infer_type(value))
