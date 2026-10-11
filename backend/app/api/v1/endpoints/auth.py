"""Authentication endpoints for session management, token issuance, and demo login."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.errors import RecallException, ResourceNotFoundError
from app.core.security import create_access_token
from app.models.identity import CourseEnrollment, User, UserRole
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import EnrollmentRepository, UserRepository
from app.schemas.auth import AuthMeResponse, DemoLoginRequest, LoginRequest, TokenResponse
from app.schemas.identity import EnrollmentCreate, EnrollmentResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Passwordless email-only authentication is disabled to prevent privilege escalation."""
    raise RecallException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        code="AUTHENTICATION_DISABLED",
        title="Passwordless Login Disabled",
        detail=(
            "Passwordless email-only authentication is disabled to prevent unverified "
            "privilege escalation. In development or demo environments, use "
            "/api/v1/auth/demo-login."
        ),
    )


@router.post("/demo-login", response_model=TokenResponse)
async def demo_login(
    payload: DemoLoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Quick demo login for students or instructors.

    Ensures the user and DBMS course enrollment exist for a seamless hackathon demo.
    Restricted to non-production environments.
    """
    allowed_envs = {"development", "test", "demo", "dev"}
    if settings.ENVIRONMENT.lower() not in allowed_envs or not settings.DEBUG:
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="DEMO_LOGIN_DISABLED",
            title="Demo Login Forbidden",
            detail=(
                "Demo login is strictly disabled in production and staging environments, "
                "or when debug mode is inactive."
            ),
        )

    user_repo = UserRepository(db)
    course_repo = CourseRepository(db)
    enroll_repo = EnrollmentRepository(db)

    # 1. Ensure target course exists (or seed it)
    course = await course_repo.get_by_code(payload.course_code)
    if not course:
        from app.seeds.seed_dbms_questions import seed_dbms_curriculum_and_questions

        await seed_dbms_curriculum_and_questions(db)
        course = await course_repo.get_by_code(payload.course_code)

    # 2. Select demo identity
    if payload.role.lower() == "admin":
        email = "admin.audit@recall.edu"
        full_name = "Auditor Ada (System Administrator)"
        role = UserRole.ADMIN
    elif payload.role.lower() == "instructor":
        if payload.course_code.upper() in ("CS301", "OS"):
            email = "instructor.os@recall.edu"
            full_name = "Prof. Andrew Tanenbaum"
        else:
            email = "instructor.dbms@recall.edu"
            full_name = "Prof. E. F. Codd"
        role = UserRole.INSTRUCTOR
    else:
        email = "student.ada@recall.edu"
        full_name = "Ada Lovelace"
        role = UserRole.STUDENT

    user = await user_repo.get_by_email(email)
    if not user:
        user = User(email=email, full_name=full_name, role=role, is_active=True)
        user = await user_repo.create(user)

    # 3. Ensure student enrollment in course
    if course and user.role == UserRole.STUDENT:
        existing_enrollment = await enroll_repo.get_enrollment(user.id, course.id)
        if not existing_enrollment:
            enrollment = CourseEnrollment(user_id=user.id, course_id=course.id, is_active=True)
            await enroll_repo.create(enrollment)

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=AuthMeResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    """Return profile and enrolled courses for the authenticated user."""
    enroll_repo = EnrollmentRepository(db)
    enrollments = await enroll_repo.list_by_user(current_user.id)
    enrolled_ids = [e.course_id for e in enrollments if e.is_active]

    return AuthMeResponse(
        user=UserResponse.model_validate(current_user),
        enrolled_course_ids=enrolled_ids,
    )


@router.post("/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_current_user(
    payload: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentResponse:
    """Enroll the authenticated student in a course."""
    if current_user.role == UserRole.STUDENT and current_user.id != payload.user_id:
        raise RecallException(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            title="Cannot Enroll Other Users",
            detail="Students may only enroll themselves.",
        )

    course_repo = CourseRepository(db)
    course = await course_repo.get_by_id(payload.course_id)
    if not course:
        raise ResourceNotFoundError("Course", payload.course_id)

    enroll_repo = EnrollmentRepository(db)
    existing = await enroll_repo.get_enrollment(payload.user_id, payload.course_id)
    if existing:
        return EnrollmentResponse.model_validate(existing)

    enrollment = CourseEnrollment(
        user_id=payload.user_id,
        course_id=payload.course_id,
        is_active=True,
    )
    created = await enroll_repo.create(enrollment)
    return EnrollmentResponse.model_validate(created)
