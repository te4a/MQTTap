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
    logger.info("Login success: %s", payload.username)
    return TokenResponse(access_token=token)


@api_router.get("/auth/me", response_model=UserInfo)
async def me(user=Depends(require_user)) -> UserInfo:
    sql = text(
        """
        SELECT users.id, users.username, users.email, users.max_points, users.feature_access, roles.name AS role
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE users.id = :id
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"id": user["id"]})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    feature_access = _normalize_feature_access(row.get("feature_access"))
    return UserInfo(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        role=row["role"],
        max_points=row["max_points"],
        feature_access=feature_access,
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
        logger.warning("Registration failed: missing fields")
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
            logger.warning("Registration failed: username exists (%s)", payload.username)
            raise HTTPException(status_code=400, detail="Username already exists")
        if email:
            existing_email = (
                await conn.execute(
                    text("SELECT 1 FROM users WHERE email = :email"),
                    {"email": email},
                )
            ).first()
            if existing_email:
                logger.warning("Registration failed: email exists (%s)", email)
                raise HTTPException(status_code=400, detail="Email already exists")

        if invite_code:
            invite = (
                await conn.execute(
                    text(
                        """
                        SELECT code, role_name, is_active, is_single_use
                        FROM invites
                        WHERE code = :code
                        FOR UPDATE
                        """
                    ),
                    {"code": invite_code},
                )
            ).mappings().first()
            if not invite or not invite["is_active"]:
                logger.warning("Registration failed: invalid invite (%s)", invite_code)
                raise HTTPException(status_code=400, detail="Invalid invite")
            if invite["role_name"] not in ("admin", "user"):
                logger.warning("Registration failed: invalid invite role (%s)", invite.get("role_name"))
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
        if invite_code:
            logger.info("Registration success: %s (invite %s)", payload.username, invite_code)
        else:
            logger.info("Registration success: %s", payload.username)
        if invite_code and invite and invite["is_single_use"]:
            await conn.execute(
                text("UPDATE invites SET is_active = false WHERE code = :code"),
                {"code": invite_code},
            )

    return {"status": "ok"}


@api_router.put("/auth/profile")
async def update_profile(payload: UpdateProfileRequest, user=Depends(require_user)) -> dict[str, str]:
    email = payload.email
    max_points = payload.max_points
    fields_set = getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))
    updates = []
    params: dict[str, Any] = {"id": user["id"]}
    if "email" in fields_set:
        updates.append("email = :email")
        params["email"] = email
    if "max_points" in fields_set:
        if max_points is None or not 1 <= max_points <= 5000:
            raise HTTPException(status_code=400, detail="max_points must be between 1 and 5000")
        updates.append("max_points = :max_points")
        params["max_points"] = max_points
    if not updates:
        return {"status": "ok"}
    async with engine.begin() as conn:
        await conn.execute(
            text(f"UPDATE users SET {', '.join(updates)} WHERE id = :id"),
            params,
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
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT max_points FROM users WHERE id = :id"),
                {"id": user["id"]},
            )
        ).mappings().first()
    return {
        "float_precision": data.get("float_precision"),
        "max_points": row["max_points"] if row else 5000,
    }


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
    if filtered:
        logged_keys = sorted([k for k in filtered.keys() if k != "mqtt_password"])
        logger.info("Settings updated by user_id=%s keys=%s", user["id"], ",".join(logged_keys))
    await save_settings(engine, filtered)
    return filtered


@api_router.get("/users")
async def list_users(user=Depends(require_admin)) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT users.id, users.username, users.email, users.feature_access, users.allowed_topics, users.allowed_signals, roles.name AS role, users.created_at
        FROM users
        JOIN roles ON roles.id = users.role_id
        ORDER BY users.id
        """
    )
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["feature_access"] = _normalize_feature_access(item.get("feature_access"))
        result.append(item)
    return result


@api_router.post("/users")
async def create_user(payload: dict[str, Any], user=Depends(require_admin)) -> dict[str, Any]:
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    role = payload.get("role", "user")
    feature_access = _normalize_feature_access(payload.get("feature_access"))
    allowed_topics = _normalize_allowed_topics(payload.get("allowed_topics", None))
    allowed_signals = _normalize_allowed_signals(payload.get("allowed_signals", None))
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    if role not in ("admin", "user", "pending"):
        raise HTTPException(status_code=400, detail="invalid role")
    sql = text(
        """
        INSERT INTO users (username, email, password_hash, role_id, feature_access, allowed_topics, allowed_signals)
        VALUES (:username, :email, :password_hash, (SELECT id FROM roles WHERE name = :role), CAST(:feature_access AS JSONB), CAST(:allowed_topics AS JSONB), CAST(:allowed_signals AS JSONB))
        RETURNING id, username, email, feature_access, allowed_topics, allowed_signals, role_id, created_at
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
                    "feature_access": json.dumps(feature_access, ensure_ascii=False),
                    "allowed_topics": json.dumps(allowed_topics, ensure_ascii=False) if allowed_topics is not None else None,
                    "allowed_signals": json.dumps(allowed_signals, ensure_ascii=False) if allowed_signals is not None else None,
                },
            )
        ).mappings().first()
    item = dict(row)
    item["feature_access"] = _normalize_feature_access(item.get("feature_access"))
    return item


@api_router.put("/users/{user_id}")
async def update_user(user_id: int, payload: dict[str, Any], user=Depends(require_admin)) -> dict[str, Any]:
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    role = payload.get("role")
    allowed_topics = _normalize_allowed_topics(payload["allowed_topics"]) if "allowed_topics" in payload else None
    allowed_signals = _normalize_allowed_signals(payload["allowed_signals"]) if "allowed_signals" in payload else None
    if role and role not in ("admin", "user", "pending"):
        raise HTTPException(status_code=400, detail="invalid role")
    updates = []
    params: dict[str, Any] = {"user_id": user_id}
    if username:
        updates.append("username = :username")
        params["username"] = username
    if "email" in payload:
        updates.append("email = :email")
        params["email"] = email
    if password:
        updates.append("password_hash = :password_hash")
        params["password_hash"] = hash_password(password)
    if role:
        updates.append("role_id = (SELECT id FROM roles WHERE name = :role)")
        params["role"] = role
    if "feature_access" in payload:
        feature_access = _normalize_feature_access(payload.get("feature_access"))
        updates.append("feature_access = CAST(:feature_access AS JSONB)")
        params["feature_access"] = json.dumps(feature_access, ensure_ascii=False)
    if "allowed_topics" in payload:
        updates.append("allowed_topics = CAST(:allowed_topics AS JSONB)")
        params["allowed_topics"] = (
            json.dumps(allowed_topics, ensure_ascii=False) if allowed_topics is not None else None
        )
    if "allowed_signals" in payload:
        updates.append("allowed_signals = CAST(:allowed_signals AS JSONB)")
        params["allowed_signals"] = (
            json.dumps(allowed_signals, ensure_ascii=False) if allowed_signals is not None else None
        )
    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")
    sql = text(
        f"""
        UPDATE users
        SET {', '.join(updates)}
        WHERE id = :user_id
        RETURNING id, username, email, feature_access, allowed_topics, allowed_signals, role_id, created_at
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, params)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    item = dict(row)
    item["feature_access"] = _normalize_feature_access(item.get("feature_access"))
    return item


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
        SELECT id, code, role_name, is_active, is_single_use, created_by, created_at, updated_at
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
                    INSERT INTO invites (code, role_name, is_active, is_single_use, created_by)
                    VALUES (:code, :role_name, :is_active, :is_single_use, :created_by)
                    RETURNING id, code, role_name, is_active, is_single_use, created_by, created_at, updated_at
                    """
                ),
                {
                    "code": code,
                    "role_name": payload.role_name,
                    "is_active": payload.is_active,
                    "is_single_use": payload.is_single_use,
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
    if payload.is_single_use is not None:
        updates.append("is_single_use = :is_single_use")
        params["is_single_use"] = payload.is_single_use
    if not updates:
        raise HTTPException(status_code=400, detail="no fields to update")

    sql = text(
        f"""
        UPDATE invites
        SET {', '.join(updates)}
        WHERE id = :invite_id
        RETURNING id, code, role_name, is_active, is_single_use, created_by, created_at, updated_at
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
    await _require_feature_access(user, "charts")
    allowed_topics, allowed_signals = await _get_user_acl(user)
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
        topic = item.get("config", {}).get("topic") if isinstance(item.get("config"), dict) else None
        if topic and not _is_topic_allowed(topic, allowed_topics):
            continue
        if topic and allowed_signals is not None:
            cfg = item.get("config", {})
            restricted = allowed_signals.get(topic)
            if restricted is not None:
                chart_type = cfg.get("type", "single")
                if chart_type == "single" and cfg.get("field") not in restricted:
                    continue
                if chart_type == "multi":
                    channels = cfg.get("channels") or []
                    fields = [c.get("field") if isinstance(c, dict) else c for c in channels]
                    fields = [field for field in fields if isinstance(field, str)]
                    if not fields or any(field not in restricted for field in fields):
                        continue
                if chart_type == "formula":
                    fields = cfg.get("fields") or []
                    if not fields or any(field not in restricted for field in fields):
                        continue
        result.append(item)
    return result


@api_router.post("/charts")
async def create_chart(payload: dict[str, Any], user=Depends(require_user)) -> dict[str, Any]:
    await _require_feature_access(user, "charts")
    if "config" not in payload:
        raise HTTPException(status_code=400, detail="config required")
    allowed_topics, allowed_signals = await _get_user_acl(user)
    config_payload = payload["config"]
    if isinstance(config_payload, dict):
        config_topic = config_payload.get("topic")
    else:
        try:
            parsed = json.loads(config_payload)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        config_topic = parsed.get("topic")
    if config_topic and not _is_topic_allowed(config_topic, allowed_topics):
        raise HTTPException(status_code=403, detail="Topic access denied")
    if config_topic and allowed_signals is not None:
        restricted = allowed_signals.get(config_topic)
        if restricted is not None:
            chart_type = (config_payload.get("type") if isinstance(config_payload, dict) else parsed.get("type")) or "single"
            if chart_type == "single":
                field = (config_payload.get("field") if isinstance(config_payload, dict) else parsed.get("field"))
                if field not in restricted:
                    raise HTTPException(status_code=403, detail="Signal access denied")
            elif chart_type == "multi":
                channels = (config_payload.get("channels") if isinstance(config_payload, dict) else parsed.get("channels")) or []
                fields = [c.get("field") if isinstance(c, dict) else c for c in channels]
                fields = [field for field in fields if isinstance(field, str)]
                if any(field not in restricted for field in fields):
                    raise HTTPException(status_code=403, detail="Signal access denied")
            elif chart_type == "formula":
                fields = (config_payload.get("fields") if isinstance(config_payload, dict) else parsed.get("fields")) or []
                if any(field not in restricted for field in fields):
                    raise HTTPException(status_code=403, detail="Signal access denied")
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
    await _require_feature_access(user, "charts")
    if "config" not in payload:
        raise HTTPException(status_code=400, detail="config required")
    allowed_topics, allowed_signals = await _get_user_acl(user)
    config_payload = payload["config"]
    if isinstance(config_payload, dict):
        config_topic = config_payload.get("topic")
    else:
        try:
            parsed = json.loads(config_payload)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        config_topic = parsed.get("topic")
    if config_topic and not _is_topic_allowed(config_topic, allowed_topics):
        raise HTTPException(status_code=403, detail="Topic access denied")
    if config_topic and allowed_signals is not None:
        restricted = allowed_signals.get(config_topic)
        if restricted is not None:
            chart_type = (config_payload.get("type") if isinstance(config_payload, dict) else parsed.get("type")) or "single"
            if chart_type == "single":
                field = (config_payload.get("field") if isinstance(config_payload, dict) else parsed.get("field"))
                if field not in restricted:
                    raise HTTPException(status_code=403, detail="Signal access denied")
            elif chart_type == "multi":
                channels = (config_payload.get("channels") if isinstance(config_payload, dict) else parsed.get("channels")) or []
                fields = [c.get("field") if isinstance(c, dict) else c for c in channels]
                fields = [field for field in fields if isinstance(field, str)]
                if any(field not in restricted for field in fields):
                    raise HTTPException(status_code=403, detail="Signal access denied")
            elif chart_type == "formula":
                fields = (config_payload.get("fields") if isinstance(config_payload, dict) else parsed.get("fields")) or []
                if any(field not in restricted for field in fields):
                    raise HTTPException(status_code=403, detail="Signal access denied")
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
    await _require_feature_access(user, "charts")
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


def _parse_interval(value: str | None) -> tuple[int, str] | None:
    if not value:
        return None
    parts = value.strip().split()
    if len(parts) == 1:
        count = 1
        unit = parts[0].lower()
    elif len(parts) == 2 and parts[0].isdigit():
        count = int(parts[0])
        unit = parts[1].lower()
    else:
        return None
    if count < 1:
        return None
    if unit.endswith("s"):
        unit = unit[:-1]
    if unit not in ("second", "minute", "hour", "day"):
        return None
    return count, unit


def _normalize_allowed_topics(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise HTTPException(status_code=400, detail="allowed_topics must be a list or null")
    topics: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HTTPException(status_code=400, detail="allowed_topics must contain strings only")
        topic = item.strip()
        if topic:
            topics.append(topic)
    return sorted(set(topics))


def _normalize_allowed_signals(value: Any) -> dict[str, list[str]] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="allowed_signals must be an object or null")
    result: dict[str, list[str]] = {}
    for topic, fields in value.items():
        if not isinstance(topic, str):
            raise HTTPException(status_code=400, detail="allowed_signals keys must be topic strings")
        clean_topic = topic.strip()
        if not clean_topic:
            continue
        if not isinstance(fields, list):
            raise HTTPException(status_code=400, detail="allowed_signals values must be arrays")
        clean_fields: list[str] = []
        for field in fields:
            if not isinstance(field, str):
                raise HTTPException(status_code=400, detail="allowed_signals field names must be strings")
            clean_field = field.strip()
            if clean_field:
                clean_fields.append(clean_field)
        result[clean_topic] = sorted(set(clean_fields))
    return result


def _decode_json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


def _normalize_feature_access(value: Any) -> dict[str, bool]:
    raw = _decode_json_value(value)
    if not isinstance(raw, dict):
        return {"history": True, "charts": True}

    def _to_bool(v: Any, default: bool = True) -> bool:
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"false", "0", "no", "off"}:
                return False
            if normalized in {"true", "1", "yes", "on"}:
                return True
        return default

    return {
        "history": _to_bool(raw.get("history"), True),
        "charts": _to_bool(raw.get("charts"), True),
    }


async def _get_user_acl(user: dict[str, Any]) -> tuple[set[str] | None, dict[str, set[str]] | None]:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT allowed_topics, allowed_signals FROM users WHERE id = :id"),
                {"id": user["id"]},
            )
        ).mappings().first()
    if not row:
        return set(), {}
    raw_topics = _decode_json_value(row.get("allowed_topics"))
    raw_signals = _decode_json_value(row.get("allowed_signals"))
    normalized_topics = _normalize_allowed_topics(raw_topics)
    normalized_signals = _normalize_allowed_signals(raw_signals)
    topic_set = None if normalized_topics is None else set(normalized_topics)
    signal_map = None
    if normalized_signals is not None:
        signal_map = {topic: set(fields) for topic, fields in normalized_signals.items()}
    return topic_set, signal_map


async def _require_feature_access(user: dict[str, Any], feature: str) -> None:
    if feature not in ("history", "charts"):
        return
    detail = "History access denied" if feature == "history" else "Charts access denied"
    feature_access = await _get_user_feature_access(user["id"])
    if not bool(feature_access.get(feature, True)):
        raise HTTPException(status_code=403, detail=detail)


async def _require_history_or_charts_access(user: dict[str, Any]) -> None:
    feature_access = await _get_user_feature_access(user["id"])
    if bool(feature_access.get("history", True)) or bool(feature_access.get("charts", True)):
        return
    raise HTTPException(status_code=403, detail="History access denied")


async def _get_user_feature_access(user_id: int) -> dict[str, bool]:
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text(
                    """
                    SELECT feature_access
                    FROM users
                    WHERE id = :id
                    """
                ),
                {"id": user_id},
            )
        ).mappings().first()
    if not row:
        return {"history": False, "charts": False}
    return _normalize_feature_access(row.get("feature_access"))


def _is_topic_allowed(topic: str, allowed_topics: set[str] | None) -> bool:
    return allowed_topics is None or topic in allowed_topics


def _filter_fields_by_acl(
    topic: str,
    fields: list[str],
    allowed_signals: dict[str, set[str]] | None,
) -> list[str]:
    if allowed_signals is None:
        return fields
    allowed = allowed_signals.get(topic)
    if allowed is None:
        return fields
    return [field for field in fields if field in allowed]


@api_router.get("/topics")
async def list_topics(user=Depends(require_user)) -> list[dict[str, Any]]:
    allowed_topics, allowed_signals = await _get_user_acl(user)
    sql = text("SELECT topic, table_name, is_json FROM topic_registry ORDER BY topic")
    async with engine.begin() as conn:
        rows = (await conn.execute(sql)).mappings().all()

    result = []
    for row in rows:
        if not _is_topic_allowed(row["topic"], allowed_topics):
            continue
        columns = await get_table_columns(engine, row["table_name"])
        fields = [c for c in columns.keys() if c not in ("id", "ts")]
        fields = _filter_fields_by_acl(row["topic"], fields, allowed_signals)
        if not fields:
            continue
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
    await _require_history_or_charts_access(user)
    allowed_topics, allowed_signals = await _get_user_acl(user)
    if not _is_topic_allowed(topic, allowed_topics):
        raise HTTPException(status_code=403, detail="Topic access denied")
    sql = text("SELECT topic, table_name, is_json FROM topic_registry WHERE topic = :topic")
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"topic": topic})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Unknown topic")

    table_name = row["table_name"]
    is_json = row["is_json"]
    columns = await get_table_columns(engine, table_name)
    all_fields = [c for c in columns.keys() if c not in ("id", "ts")]
    visible_fields = _filter_fields_by_acl(topic, all_fields, allowed_signals)
    if not visible_fields:
        raise HTTPException(status_code=403, detail="Signal access denied")
    requested_fields = _parse_fields(fields) or visible_fields

    for field in requested_fields:
        if field not in all_fields:
            raise HTTPException(status_code=400, detail=f"Unknown field: {field}")
        if field not in visible_fields:
            raise HTTPException(status_code=403, detail="Signal access denied")

    dt_from = _parse_dt(from_ts)
    dt_to = _parse_dt(to_ts)

    if agg:
        parsed = _parse_interval(interval)
        if not parsed:
            raise HTTPException(status_code=400, detail="Invalid interval")
        interval_count, interval_unit = parsed
        return await _history_aggregate(
            table_name,
            is_json,
            requested_fields,
            dt_from,
            dt_to,
            agg,
            interval_count,
            interval_unit,
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
    interval_count: int,
    interval_unit: str,
) -> dict[str, Any]:
    agg = agg.lower()
    if agg not in ("min", "max", "avg"):
        raise HTTPException(status_code=400, detail="Invalid aggregation")

    where = []
    params: dict[str, Any] = {"count": interval_count}
    if dt_from:
        where.append("ts >= :from_ts")
        params["from_ts"] = dt_from
    if dt_to:
        where.append("ts <= :to_ts")
        params["to_ts"] = dt_to
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    interval_arg = {"second": "secs", "minute": "mins", "hour": "hours", "day": "days"}[interval_unit]
    bucket_expr = f"date_bin(make_interval({interval_arg} => :count), ts, '1970-01-01')"
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
            SELECT {bucket_expr} AS bucket, {agg_cols}
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
            SELECT {bucket_expr} AS bucket, {agg}({expr}) AS value
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
        requested_path = (_dist_path / path).resolve()
        try:
            requested_path.relative_to(_dist_path)
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found")
        if requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(_index_path)
else:
    @app.get("/")
    async def root() -> dict[str, str]:
        logger.error(f"Frontend not built. Expected at {_dist_path}")
        return {"message": "Frontend not built. Run: cd frontend && pnpm build"}
