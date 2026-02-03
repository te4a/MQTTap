import asyncio
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from mqttap.api.auth import authenticate, require_admin, require_user
from mqttap.api.schemas import LoginRequest, TokenResponse, UserInfo
from mqttap.config import settings
from mqttap.db.dynamic import get_table_columns, quote_ident

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from mqttap.db.core import engine
from mqttap.db.init import init_base_schema
from mqttap.services.mqtt import MqttConsumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_base_schema(engine)
    consumer = MqttConsumer()
    await consumer.start()
    app.state.mqtt_consumer = consumer
    yield
    await consumer.stop()


app = FastAPI(title="MQTTap", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    token = await authenticate(payload.email, payload.password)
    return TokenResponse(access_token=token)


@app.get("/auth/me", response_model=UserInfo)
async def me(user=Depends(require_user)) -> UserInfo:
    sql = text(
        """
        SELECT users.id, users.email, roles.name AS role
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE users.id = :id
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"id": user["id"]})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInfo(id=row["id"], email=row["email"], role=row["role"])


@app.get("/settings")
async def get_settings(user=Depends(require_admin)) -> dict[str, str]:
    sql = text("SELECT key, value FROM settings")
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).all()
    return {row[0]: row[1] for row in rows}


@app.put("/settings")
async def update_settings(payload: dict[str, str], user=Depends(require_admin)) -> dict[str, str]:
    sql = text(
        """
        INSERT INTO settings (key, value, type)
        VALUES (:key, :value, 'string')
        ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = now()
        """
    )
    async with engine.begin() as conn:
        for key, value in payload.items():
            await conn.execute(sql, {"key": key, "value": value})
    return payload


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def _parse_fields(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@app.get("/topics")
async def list_topics(user=Depends(require_user)) -> list[dict[str, Any]]:
    sql = text("SELECT topic, table_name, is_json FROM topic_registry ORDER BY topic")
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()

    result = []
    for row in rows:
        columns = await get_table_columns(engine, row["table_name"])
        fields = [c for c in columns.keys() if c not in ("id", "ts")]
        result.append(
            {
                "topic": row["topic"],
                "table": row["table_name"],
                "is_json": row["is_json"],
                "fields": fields,
            }
        )
    return result


@app.get("/history")
async def history(
    topic: str,
    fields: str | None = Query(None),
    from_ts: str | None = Query(None),
    to_ts: str | None = Query(None),
    agg: str | None = Query(None),
    interval: str | None = Query(None),
    limit: int = Query(5000, ge=1, le=5000),
    order: str = Query("desc"),
    user=Depends(require_user),
) -> dict[str, Any]:
    sql = text("SELECT topic, table_name, is_json FROM topic_registry WHERE topic = :topic")
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"topic": topic})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Unknown topic")

    table_name = row["table_name"]
    is_json = row["is_json"]
    columns = await get_table_columns(engine, table_name)
    all_fields = [c for c in columns.keys() if c not in ("id", "ts")]
    requested_fields = _parse_fields(fields) or all_fields

    for field in requested_fields:
        if field not in all_fields:
            raise HTTPException(status_code=400, detail=f"Unknown field: {field}")

    dt_from = _parse_dt(from_ts)
    dt_to = _parse_dt(to_ts)

    if agg:
        if interval not in ("minute", "hour", "day"):
            raise HTTPException(status_code=400, detail="Invalid interval")
        return await _history_aggregate(
            table_name,
            is_json,
            requested_fields,
            dt_from,
            dt_to,
            agg,
            interval,
        )
    if not dt_from and not dt_to:
        order = "desc"
    return await _history_raw(
        table_name,
        is_json,
        requested_fields,
        dt_from,
        dt_to,
        limit,
        order,
    )


async def _history_raw(
    table_name: str,
    is_json: bool,
    fields: list[str],
    dt_from: datetime | None,
    dt_to: datetime | None,
    limit: int,
    order: str,
) -> dict[str, Any]:
    order = "ASC" if order.lower() == "asc" else "DESC"
    cols = ["ts"] + fields
    select_cols = ", ".join([quote_ident(c) for c in cols])
    where = []
    params: dict[str, Any] = {"limit": limit}
    if dt_from:
        where.append("ts >= :from_ts")
        params["from_ts"] = dt_from
    if dt_to:
        where.append("ts <= :to_ts")
        params["to_ts"] = dt_to
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = text(
        f"""
        SELECT {select_cols}
        FROM {quote_ident(table_name)}
        {where_sql}
        ORDER BY ts {order}
        LIMIT :limit
        """
    )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql, params)).mappings().all()
    return {
        "table": table_name,
        "is_json": is_json,
        "rows": [dict(row) for row in rows],
    }


async def _history_aggregate(
    table_name: str,
    is_json: bool,
    fields: list[str],
    dt_from: datetime | None,
    dt_to: datetime | None,
    agg: str,
    interval: str,
) -> dict[str, Any]:
    agg = agg.lower()
    if agg not in ("min", "max", "avg", "sum", "count"):
        raise HTTPException(status_code=400, detail="Invalid aggregation")

    where = []
    params: dict[str, Any] = {"bucket": interval}
    if dt_from:
        where.append("ts >= :from_ts")
        params["from_ts"] = dt_from
    if dt_to:
        where.append("ts <= :to_ts")
        params["to_ts"] = dt_to
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    if is_json:
        columns = await get_table_columns(engine, table_name)
        for field in fields:
            data_type = columns.get(field, "")
            if data_type not in ("bigint", "double precision"):
                raise HTTPException(status_code=400, detail=f"Field not numeric: {field}")

        agg_cols = ", ".join(
            [f"{agg}({quote_ident(field)}) AS {quote_ident(field)}" for field in fields]
        )
        sql = text(
            f"""
            SELECT date_trunc(:bucket, ts) AS bucket, {agg_cols}
            FROM {quote_ident(table_name)}
            {where_sql}
            GROUP BY bucket
            ORDER BY bucket
            """
        )
    else:
        expr = "CASE WHEN value_type = 'float' THEN value_float WHEN value_type = 'int' THEN value_int END"
        sql = text(
            f"""
            SELECT date_trunc(:bucket, ts) AS bucket, {agg}({expr}) AS value
            FROM {quote_ident(table_name)}
            {where_sql}
            GROUP BY bucket
            ORDER BY bucket
            """
        )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql, params)).mappings().all()
    return {"table": table_name, "is_json": is_json, "rows": [dict(row) for row in rows]}


_dist_path = (Path(__file__).resolve().parents[3] / "frontend" / "dist")
if _dist_path.exists():
    app.mount("/", StaticFiles(directory=_dist_path, html=True), name="frontend")
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Frontend not built. Run: cd frontend && npm run build"}
