import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from mqttap.config import settings
from mqttap.db.dynamic import (
    ensure_columns,
    ensure_topic_table,
    infer_column_spec,
    json_key_to_column,
    normalize_value_for_column,
    topic_to_table,
    widen_column,
    _infer_type,
)


def _round_float(value: float, precision: int) -> float:
    return round(value, precision)


def _normalize_value(value: Any, precision: int) -> Any:
    if isinstance(value, float):
        return _round_float(value, precision)
    return value


def _parse_payload(payload: bytes) -> Any:
    text_value = payload.decode("utf-8", errors="ignore").strip()
    if not text_value:
        return None
    try:
        return json.loads(text_value)
    except json.JSONDecodeError:
        return text_value


async def _register_topic(engine: AsyncEngine, topic: str, table_name: str, is_json: bool) -> None:
    sql = text(
        """
        INSERT INTO topic_registry (topic, table_name, is_json)
        VALUES (:topic, :table_name, :is_json)
        ON CONFLICT (topic) DO NOTHING
        """
    )
    async with engine.begin() as conn:
        await conn.execute(sql, {"topic": topic, "table_name": table_name, "is_json": is_json})


async def store_message(engine: AsyncEngine, topic: str, payload: bytes, float_precision: int) -> None:
    topic_str = str(topic)
    parsed = _parse_payload(payload)
    is_json = isinstance(parsed, dict)
    table_name = topic_to_table(topic_str, is_json=is_json)

    await ensure_topic_table(engine, table_name, is_json=is_json)
    await _register_topic(engine, topic_str, table_name, is_json=is_json)

    if is_json:
        await _store_json(engine, table_name, parsed, float_precision)
    else:
        await _store_scalar(engine, table_name, parsed, float_precision)


async def _store_json(
    engine: AsyncEngine, table_name: str, payload: dict[str, Any], float_precision: int
) -> None:
    columns = []
    values: dict[str, Any] = {}
    for key, value in payload.items():
        col = json_key_to_column(key)
        value = _normalize_value(value, float_precision)
        columns.append(infer_column_spec(col, value))
        values[col] = value

    existing = await ensure_columns(engine, table_name, columns)

    # Widen types if needed
    for col_name, value in values.items():
        current_type = existing.get(col_name, "text")
        incoming_type = _infer_type(value)
        new_type = None
        if current_type != incoming_type:
            if current_type == "bigint" and incoming_type == "double precision":
                new_type = "double precision"
            else:
                new_type = "text"
        if new_type:
            await widen_column(engine, table_name, col_name, new_type)
            existing[col_name] = new_type

    values = {k: normalize_value_for_column(v, existing.get(k, "text")) for k, v in values.items()}
    column_names = ", ".join([f'"{k}"' for k in values.keys()])
    placeholders = ", ".join([f":{k}" for k in values.keys()])
    sql = text(f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})')
    async with engine.begin() as conn:
        await conn.execute(sql, values)


def _infer_logical_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    return "json"


async def _store_scalar(
    engine: AsyncEngine, table_name: str, value: Any, float_precision: int
) -> None:
    value = _normalize_value(value, float_precision)
    value_type = _infer_logical_type(value)

    data = {
        "value_type": value_type,
        "value_int": None,
        "value_float": None,
        "value_bool": None,
        "value_text": None,
        "value_json": None,
    }

    if value_type == "int":
        data["value_int"] = int(value) if value is not None else None
    elif value_type == "float":
        data["value_float"] = float(value) if value is not None else None
    elif value_type == "bool":
        data["value_bool"] = bool(value) if value is not None else None
    elif value_type == "json":
        data["value_json"] = json.dumps(value, ensure_ascii=False)
    else:
        data["value_text"] = None if value is None else str(value)

    sql = text(
        f"""
        INSERT INTO "{table_name}" (
            value_type, value_int, value_float, value_bool, value_text, value_json
        ) VALUES (
            :value_type, :value_int, :value_float, :value_bool, :value_text, :value_json
        )
        """
    )
    async with engine.begin() as conn:
        await conn.execute(sql, data)
