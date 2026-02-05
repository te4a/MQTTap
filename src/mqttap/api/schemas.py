from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    email: EmailStr | None = None
    role: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    email: EmailStr | None = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: EmailStr | None = None
    invite: str | None = None


class InviteCreateRequest(BaseModel):
    code: str | None = None
    role_name: str
    is_active: bool = True


class InviteUpdateRequest(BaseModel):
    code: str | None = None
    role_name: str | None = None
    is_active: bool | None = None
