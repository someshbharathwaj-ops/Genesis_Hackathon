"""Course and curriculum endpoints."""


from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import RecallException, ResourceNotFoundError
from app.models.curriculum import LearningObjective, Topic
from app.models.identity import Course, CourseEnrollment
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.user_repo import EnrollmentRepository, UserRepository
from app.schemas.curriculum import (
    LearningObjectiveCreate,
    LearningObjectiveResponse,
    TopicCreate,
    TopicResponse,
)
from app.schemas.identity import (
    CourseCreate,
    CourseResponse,
    EnrollmentCreate,
    EnrollmentResponse,
)

router = APIRouter(prefix="/courses", tags=["Courses & Curriculum"])


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate, db: AsyncSession = Depends(get_db)
) -> CourseResponse:
    repo = CourseRepository(db)
    existing = await repo.get_by_code(payload.code)
    if existing:
        raise RecallException(
            status_code=status.HTTP_409_CONFLICT,
            code="COURSE_CODE_EXISTS",
            title="Course Already Exists",
            detail=f"Course with code '{payload.code}' already exists.",
        )
    course = Course(
        code=payload.code,
        title=payload.title,
        description=payload.description,
        instructor_id=payload.instructor_id,
    )
    created = await repo.create(course)
    return CourseResponse.model_validate(created)


@router.get("", response_model=list[CourseResponse])
async def list_courses(
    limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)
) -> list[CourseResponse]:
    repo = CourseRepository(db)
    courses = await repo.list_all(limit=limit, offset=offset)
    return [CourseResponse.model_validate(c) for c in courses]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str, db: AsyncSession = Depends(get_db)
) -> CourseResponse:
    repo = CourseRepository(db)
    course = await repo.get_by_id(course_id)
    if not course:
        raise ResourceNotFoundError("Course", course_id)
    return CourseResponse.model_validate(course)


@router.post(
    "/{course_id}/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    course_id: str, payload: TopicCreate, db: AsyncSession = Depends(get_db)
) -> TopicResponse:
    course_repo = CourseRepository(db)
    course = await course_repo.get_by_id(course_id)
    if not course:
        raise ResourceNotFoundError("Course", course_id)

    topic_repo = TopicRepository(db)
    topic = Topic(
        course_id=course_id,
        code=payload.code,
        title=payload.title,
        description=payload.description,
        order_index=payload.order_index,
        objectives=[],
    )
    created = await topic_repo.create(topic)
    return TopicResponse.model_validate(created)


@router.get("/{course_id}/topics", response_model=list[TopicResponse])
async def list_course_topics(
    course_id: str, db: AsyncSession = Depends(get_db)
) -> list[TopicResponse]:
    topic_repo = TopicRepository(db)
    topics = await topic_repo.list_by_course(course_id)
    return [TopicResponse.model_validate(t) for t in topics]


@router.post(
    "/topics/{topic_id}/objectives",
    response_model=LearningObjectiveResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_objective(
    topic_id: str, payload: LearningObjectiveCreate, db: AsyncSession = Depends(get_db)
) -> LearningObjectiveResponse:
    topic_repo = TopicRepository(db)
    topic = await topic_repo.get_by_id(topic_id)
    if not topic:
        raise ResourceNotFoundError("Topic", topic_id)

    lo_repo = LearningObjectiveRepository(db)
    obj = LearningObjective(
        topic_id=topic_id,
        code=payload.code,
        title=payload.title,
        description=payload.description,
        order_index=payload.order_index,
        prerequisite_objective_ids=payload.prerequisite_objective_ids,
        metadata_attributes=payload.metadata_attributes,
    )
    created = await lo_repo.create(obj)
    return LearningObjectiveResponse.model_validate(created)


@router.post(
    "/{course_id}/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_student(
    course_id: str, payload: EnrollmentCreate, db: AsyncSession = Depends(get_db)
) -> EnrollmentResponse:
    course_repo = CourseRepository(db)
    course = await course_repo.get_by_id(course_id)
    if not course:
        raise ResourceNotFoundError("Course", course_id)

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload.user_id)
    if not user:
        raise ResourceNotFoundError("User", payload.user_id)

    enroll_repo = EnrollmentRepository(db)
    existing = await enroll_repo.get_enrollment(payload.user_id, course_id)
    if existing:
        return EnrollmentResponse.model_validate(existing)

    enrollment = CourseEnrollment(
        user_id=payload.user_id,
        course_id=course_id,
        is_active=True,
    )
    created = await enroll_repo.create(enrollment)
    return EnrollmentResponse.model_validate(created)


@router.post("/seed/dbms", status_code=status.HTTP_201_CREATED)
async def seed_dbms_course(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from app.seeds.seed_dbms_questions import seed_dbms_curriculum_and_questions

    result = await seed_dbms_curriculum_and_questions(db)
    return result
