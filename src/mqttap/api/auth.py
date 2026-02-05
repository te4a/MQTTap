from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text

from mqttap.config import settings
from mqttap.db.core import engine
from mqttap.security import verify_password


security = HTTPBearer()


def _create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_exp_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def authenticate(username: str, password: str) -> str:
    sql = text(
        """
        SELECT users.id, users.password_hash, roles.name AS role
        FROM users
        JOIN roles ON roles.id = users.role_id
        WHERE users.username = :username
        """
    )
    async with engine.begin() as conn:
        row = (await conn.execute(sql, {"username": username})).mappings().first()
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if row["role"] == "pending":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account pending approval")
    return _create_access_token(int(row["id"]), row["role"])


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
        )
        user_id = int(payload.get("sub", "0"))
        role = payload.get("role", "user")
        if not user_id:
            raise ValueError("invalid sub")
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"id": user_id, "role": role}


async def require_user(user=Depends(_get_current_user)) -> dict:
    return user


async def require_admin(user=Depends(_get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
