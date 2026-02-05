import asyncio
import json
import logging
import secrets
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from mqttap.api.auth import authenticate, require_admin, require_user
from mqttap.api.schemas import (
    ChangePasswordRequest,
    InviteCreateRequest,
    InviteUpdateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserInfo,
)
from mqttap.config import settings
from mqttap.db.dynamic import get_table_columns, quote_ident
from mqttap.security import hash_password, verify_password

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from mqttap.db.core import engine
from mqttap.db.init import init_base_schema
from mqttap.services.mqtt import MqttConsumer
from mqttap.services.settings import load_settings, save_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_base_schema(engine)
    consumer = MqttConsumer()
    await consumer.start()
    app.state.mqtt_consumer = consumer
    yield
    await consumer.stop()


app = FastAPI(title="MQTTap", lifespan=lifespan)
api_router = APIRouter()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@api_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    token = await authenticate(payload.username, payload.password)
    return TokenResponse(access_token=token)


@api_router.get("/auth/me", response_model=UserInfo)
async def me(user=Depends(require_user)) -> UserInfo:
    sql = text(
        """
        SELECT users.id, users.username, users.email, roles.name AS role
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE users.id = :id
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"id": user["id"]})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInfo(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        role=row["role"],
    )


@api_router.post("/auth/password")
async def change_password(payload: ChangePasswordRequest, user=Depends(require_user)) -> dict[str, str]:
    if not payload.old_password or not payload.new_password:
        raise HTTPException(status_code=400, detail="old_password and new_password required")
    sql = text("SELECT password_hash FROM users WHERE id = :id")
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"id": user["id"]})).mappings().first()
        if not row or not verify_password(payload.old_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Invalid current password")
        await conn.execute(
            text("UPDATE users SET password_hash = :password_hash WHERE id = :id"),
            {"id": user["id"], "password_hash": hash_password(payload.new_password)},
        )
    return {"status": "ok"}


@api_router.post("/auth/register")
async def register(payload: RegisterRequest) -> dict[str, str]:
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="username and password required")

    email = payload.email
    invite_code = payload.invite
    role_name = "pending"

    async with engine.begin() as conn:
        existing = (
            await conn.execute(
                text("SELECT 1 FROM users WHERE username = :username"),
                {"username": payload.username},
            )
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        if email:
            existing_email = (
                await conn.execute(
                    text("SELECT 1 FROM users WHERE email = :email"),
                    {"email": email},
                )
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already exists")

        if invite_code:
            invite = (
                await conn.execute(
                    text(
                        """
                        SELECT code, role_name, is_active
                        FROM invites
                        WHERE code = :code
                        """
                    ),
                    {"code": invite_code},
                )
            ).mappings().first()
            if not invite or not invite["is_active"]:
                raise HTTPException(status_code=400, detail="Invalid invite")
            if invite["role_name"] not in ("admin", "user"):
                raise HTTPException(status_code=400, detail="Invalid invite role")
            role_name = invite["role_name"]

        await conn.execute(
            text(
                """
                INSERT INTO users (username, email, password_hash, role_id)
                VALUES (:username, :email, :password_hash, (SELECT id FROM roles WHERE name = :role))
                """
            ),
            {
                "username": payload.username,
                "email": email,
                "password_hash": hash_password(payload.password),
                "role": role_name,
            },
        )

    return {"status": "ok"}


@api_router.put("/auth/profile")
async def update_profile(payload: UpdateProfileRequest, user=Depends(require_user)) -> dict[str, str]:
    email = payload.email
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET email = :email WHERE id = :id"),
            {"id": user["id"], "email": email},
        )
    return {"status": "ok"}


@api_router.get("/settings")
async def get_settings(user=Depends(require_admin)) -> dict[str, Any]:
    data = await load_settings(engine)
    data.pop("database_dsn", None)
    return data


@api_router.get("/settings/public")
async def get_public_settings(user=Depends(require_user)) -> dict[str, Any]:
    data = await load_settings(engine)
    return {"float_precision": data.get("float_precision")}


@api_router.put("/settings")
async def update_settings(payload: dict[str, Any], user=Depends(require_admin)) -> dict[str, Any]:
    allowed = {
        "mqtt_host",
        "mqtt_port",
        "mqtt_topics",
        "mqtt_username",
        "mqtt_password",
        "float_precision",
        "default_agg",
        "default_interval",
    }
    filtered = {k: v for k, v in payload.items() if k in allowed}
    await save_settings(engine, filtered)
    return filtered


@api_router.get("/users")
async def list_users(user=Depends(require_admin)) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT users.id, users.username, users.email, roles.name AS role, users.created_at
        FROM users
        JOIN roles ON roles.id = users.role_id
        ORDER BY users.id
        """
    )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()
    return [dict(row) for row in rows]


@api_router.post("/users")
async def create_user(payload: dict[str, Any], user=Depends(require_admin)) -> dict[str, Any]:
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    role = payload.get("role", "user")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    if role not in ("admin", "user", "pending"):
        raise HTTPException(status_code=400, detail="invalid role")
    sql = text(
        """
        INSERT INTO users (username, email, password_hash, role_id)
        VALUES (:username, :email, :password_hash, (SELECT id FROM roles WHERE name = :role))
        RETURNING id, username, email, role_id, created_at
        """
    )
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sql,
                {
                    "username": username,
                    "email": email,
                    "password_hash": hash_password(password),
                    "role": role,
                },
            )
        ).mappings().first()
    return dict(row)


@api_router.put("/users/{user_id}")
async def update_user(user_id: int, payload: dict[str, Any], user=Depends(require_admin)) -> dict[str, Any]:
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    role = payload.get("role")
    if role and role not in ("admin", "user", "pending"):
        raise HTTPException(status_code=400, detail="invalid role")
    updates = []
    params: dict[str, Any] = {"user_id": user_id}
    if username:
        updates.append("username = :username")
        params["username"] = username
    if email:
        updates.append("email = :email")
        params["email"] = email
    if password:
        updates.append("password_hash = :password_hash")
        params["password_hash"] = hash_password(password)
    if role:
        updates.append("role_id = (SELECT id FROM roles WHERE name = :role)")
        params["role"] = role
    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")
    sql = text(
        f"""
        UPDATE users
        SET {', '.join(updates)}
        WHERE id = :user_id
        RETURNING id, username, email, role_id, created_at
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, params)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: int, user=Depends(require_admin)) -> dict[str, str]:
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    sql = text("DELETE FROM users WHERE id = :user_id")
    async with engine.begin() as conn:
        await conn.execute(sql, {"user_id": user_id})
    return {"status": "ok"}


@api_router.get("/invites")
async def list_invites(user=Depends(require_admin)) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT id, code, role_name, is_active, created_by, created_at, updated_at
        FROM invites
        ORDER BY id
        """
    )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()
    return [dict(row) for row in rows]


@api_router.post("/invites")
async def create_invite(payload: InviteCreateRequest, user=Depends(require_admin)) -> dict[str, Any]:
    if payload.role_name not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="invalid role")
    code = payload.code or secrets.token_urlsafe(8)
    async with engine.begin() as conn:
        existing = (
            await conn.execute(text("SELECT 1 FROM invites WHERE code = :code"), {"code": code})
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Invite code already exists")
        row = (
            await conn.execute(
                text(
                    """
                    INSERT INTO invites (code, role_name, is_active, created_by)
                    VALUES (:code, :role_name, :is_active, :created_by)
                    RETURNING id, code, role_name, is_active, created_by, created_at, updated_at
                    """
                ),
                {
                    "code": code,
                    "role_name": payload.role_name,
                    "is_active": payload.is_active,
                    "created_by": user["id"],
                },
            )
        ).mappings().first()
    return dict(row)


@api_router.put("/invites/{invite_id}")
async def update_invite(
    invite_id: int,
    payload: InviteUpdateRequest,
    user=Depends(require_admin),
) -> dict[str, Any]:
    updates = []
    params: dict[str, Any] = {"invite_id": invite_id}
    if payload.code is not None:
        updates.append("code = :code")
        params["code"] = payload.code
    if payload.role_name is not None:
        if payload.role_name not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="invalid role")
        updates.append("role_name = :role_name")
        params["role_name"] = payload.role_name
    if payload.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = payload.is_active
    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    sql = text(
        f"""
        UPDATE invites
        SET {', '.join(updates)}
        WHERE id = :invite_id
        RETURNING id, code, role_name, is_active, created_by, created_at, updated_at
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, params)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Invite not found")
    return dict(row)


@api_router.delete("/invites/{invite_id}")
async def delete_invite(invite_id: int, user=Depends(require_admin)) -> dict[str, str]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM invites WHERE id = :id"), {"id": invite_id})
    return {"status": "ok"}


@api_router.get("/charts")
async def list_charts(user=Depends(require_user)) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT id, name, config, created_at
        FROM user_charts
        WHERE user_id = :user_id
        ORDER BY created_at
        """
    )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql, {"user_id": user["id"]})).mappings().all()
    result = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get("config"), str):
            try:
                item["config"] = json.loads(item["config"])
            except json.JSONDecodeError:
                item["config"] = {}
        result.append(item)
    return result


@api_router.post("/charts")
async def create_chart(payload: dict[str, Any], user=Depends(require_user)) -> dict[str, Any]:
    if "config" not in payload:
        raise HTTPException(status_code=400, detail="config required")
    name = payload.get("name")
    sql = text(
        """
        INSERT INTO user_charts (user_id, name, config)
        VALUES (:user_id, :name, CAST(:config AS JSONB))
        RETURNING id, name, config, created_at
        """
    )
    config = payload["config"]
    if isinstance(config, dict):
        config = json.dumps(config, ensure_ascii=False)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sql,
                {"user_id": user["id"], "name": name, "config": config},
            )
        ).mappings().first()
    item = dict(row)
    if isinstance(item.get("config"), str):
        try:
            item["config"] = json.loads(item["config"])
        except json.JSONDecodeError:
            item["config"] = {}
    return item


@api_router.put("/charts/{chart_id}")
async def update_chart(chart_id: int, payload: dict[str, Any], user=Depends(require_user)) -> dict[str, Any]:
    if "config" not in payload:
        raise HTTPException(status_code=400, detail="config required")
    name = payload.get("name")
    config = payload["config"]
    if isinstance(config, dict):
        config = json.dumps(config, ensure_ascii=False)
    sql = text(
        """
        UPDATE user_charts
        SET name = COALESCE(:name, name),
            config = CAST(:config AS JSONB)
        WHERE id = :chart_id AND user_id = :user_id
        RETURNING id, name, config, created_at
        """
    )
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sql,
                {"chart_id": chart_id, "user_id": user["id"], "name": name, "config": config},
            )
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Chart not found")
    item = dict(row)
    if isinstance(item.get("config"), str):
        try:
            item["config"] = json.loads(item["config"])
        except json.JSONDecodeError:
            item["config"] = {}
    return item


@api_router.delete("/charts/{chart_id}")
async def delete_chart(chart_id: int, user=Depends(require_user)) -> dict[str, str]:
    sql = text(
        """
        DELETE FROM user_charts
        WHERE id = :chart_id AND user_id = :user_id
        """
    )
    async with engine.begin() as conn:
        await conn.execute(sql, {"chart_id": chart_id, "user_id": user["id"]})
    return {"status": "ok"}


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def _parse_fields(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@api_router.get("/topics")
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


@api_router.get("/history")
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
        if interval not in ("second", "minute", "hour", "day"):
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
    if agg not in ("min", "max", "avg"):
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


app.include_router(api_router, prefix="/api")


_dist_path = (Path.cwd() / "frontend" / "dist").resolve()
_assets_path = _dist_path / "assets"
_index_path = _dist_path / "index.html"
if _dist_path.exists() and _index_path.exists():
    if _assets_path.exists():
        app.mount("/assets", StaticFiles(directory=_assets_path), name="assets")
    favicon_path = _dist_path / "favicon.ico"

    @app.get("/")
    async def root() -> FileResponse:
        return FileResponse(_index_path)

    if favicon_path.exists():
        @app.get("/favicon.ico")
        async def favicon() -> FileResponse:
            return FileResponse(favicon_path)

    @app.get("/{path:path}")
    async def frontend_fallback(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(_index_path)
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        logger.error(f"Frontend not built. Expected at {_dist_path}")
        return {"message": "Frontend not built. Run: cd frontend && pnpm build"}
