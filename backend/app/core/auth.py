"""Server-side authentication and authorization dependencies for Recall.

Enforces:
1. RFC 7807 problem details upon unauthorized or forbidden access.
2. Tenant and student identity integrity (students cannot impersonate another student).
3. Course enrollment verification.
"""

from typing import Annotated

from fastapi import Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import RecallException, ResourceNotFoundError
from app.core.security import decode_access_token
from app.models.identity import Course, User, UserRole
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import EnrollmentRepository, UserRepository


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate bearer token, returning active user.

    Raises:
        RecallException: If header is missing, malformed, invalid, or user inactive.
    """
    if not authorization:
        raise RecallException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            title="Authentication Required",
            detail="Missing Authorization header with Bearer token.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise RecallException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            title="Invalid Authentication Scheme",
            detail="Authorization header must follow format 'Bearer <token>'.",
        )

    claims = decode_access_token(token.strip())
    user_id = claims.get("sub")
    if not user_id:
        raise RecallException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            title="Invalid Token",
            detail="Token subject (user ID) is missing.",
        )

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise RecallException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            title="User Not Found",
            detail="User associated with token no longer exists.",
        )

    if not user.is_active:
        raise RecallException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            title="User Inactive",
            detail="User account is deactivated.",
        )

    return user


async def get_optional_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Gracefully extract user if token present; returns None if absent."""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization, db)
    except RecallException:
        return None


async def verify_course_access(
    course_id: str,
    user: User,
    db: AsyncSession,
) -> Course:
    """Ensure user is enrolled in course or is an authorized instructor/admin."""
    course_repo = CourseRepository(db)
    course = await course_repo.get_by_id(course_id)
    if not course:
        raise ResourceNotFoundError("Course", course_id)

    if user.role in (UserRole.ADMIN, UserRole.INSTRUCTOR):
        return course

    # Student verification
    enroll_repo = EnrollmentRepository(db)
    enrollment = await enroll_repo.get_enrollment(user.id, course_id)
    if not enrollment or not enrollment.is_active:
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Course Access Denied",
            detail=f"Student '{user.full_name}' is not enrolled in course '{course.code}'.",
        )
    return course


# Alias for backwards compatibility
verify_course_enrollment = verify_course_access


def require_instructor_or_admin(user: User) -> None:
    """Enforce that current user has instructor or administrator privileges."""
    if user.role not in (UserRole.INSTRUCTOR, UserRole.ADMIN):
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Insufficient Permissions",
            detail="This operation requires instructor or administrator privileges.",
        )


def require_admin(user: User) -> None:
    """Enforce that current user has administrator privileges."""
    if user.role != UserRole.ADMIN:
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Administrator Privileges Required",
            detail="This operation is strictly restricted to system administrators.",
        )


async def verify_instructor_course_access(
    course_id: str,
    user: User,
    db: AsyncSession,
) -> Course:
    """Ensure user is instructor assigned to the course or an administrator."""
    require_instructor_or_admin(user)

    course_repo = CourseRepository(db)
    course = await course_repo.get_by_id(course_id)
    if not course:
        raise ResourceNotFoundError("Course", course_id)

    if user.role == UserRole.ADMIN:
        return course

    if course.instructor_id is not None and course.instructor_id != user.id:
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Forbidden",
            detail=(
                f"Instructor '{user.full_name}' is not assigned to manage course '{course.code}'."
            ),
        )
    return course


def verify_student_ownership(current_user: User, requested_student_id: str) -> None:
    """Prevent students from querying or mutating other students' state."""
    if current_user.role in (UserRole.INSTRUCTOR, UserRole.ADMIN):
        return
    if current_user.id != requested_student_id:
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Identity Mismatch",
            detail="Students may only access their own learning state and attempts.",
        )
