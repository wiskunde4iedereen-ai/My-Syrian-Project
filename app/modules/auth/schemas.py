from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    user_id: int


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
