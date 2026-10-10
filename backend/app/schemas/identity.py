"""Identity and enrollment Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.identity import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.STUDENT


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class CourseCreate(BaseModel):
    code: str
    title: str
    description: str | None = None
    instructor_id: str | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    title: str
    description: str | None = None
    instructor_id: str | None = None
    created_at: datetime


class EnrollmentCreate(BaseModel):
    user_id: str
    course_id: str


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    course_id: str
    is_active: bool
    created_at: datetime
