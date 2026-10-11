"""Authentication and session schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.identity import UserResponse


class LoginRequest(BaseModel):
    """Student or instructor login request."""

    email: EmailStr


class DemoLoginRequest(BaseModel):
    """Demo login shortcut."""

    role: str = "student"  # "student" or "instructor"
    course_code: str = "CS340"


class TokenResponse(BaseModel):
    """Authentication token response envelope."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuthMeResponse(BaseModel):
    """Current authenticated user profile and active enrollments."""

    model_config = ConfigDict(from_attributes=True)

    user: UserResponse
    enrolled_course_ids: list[str]
