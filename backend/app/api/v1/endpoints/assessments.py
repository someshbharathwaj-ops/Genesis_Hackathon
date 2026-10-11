"""API router for Instructor Assessment Scheduling and Student In-App Notifications."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_user,
    require_instructor_or_admin,
    verify_course_access,
    verify_student_ownership,
)
from app.core.database import get_db
from app.models.assessment import InAppNotification, ScheduledAssessment
from app.models.identity import CourseEnrollment, User
from app.schemas.assessment import (
    InAppNotificationResponse,
    ScheduledAssessmentCreate,
    ScheduledAssessmentResponse,
)

router = APIRouter(tags=["Assessment Scheduling & Notifications"])


@router.post(
    "/courses/{course_id}/assessments",
    response_model=ScheduledAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an Assessment (Instructor)",
)
async def schedule_assessment(
    course_id: str,
    payload: ScheduledAssessmentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ScheduledAssessmentResponse:
    require_instructor_or_admin(current_user)
    await verify_course_access(course_id, current_user, session)

    assessment = ScheduledAssessment(
        course_id=course_id,
        created_by_id=current_user.id,
        title=payload.title,
        description=payload.description,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        target_objective_id=payload.target_objective_id,
        status="scheduled",
    )
    session.add(assessment)
    await session.flush()

    # Query enrolled active students for this course
    enrolled_stmt = (
        select(CourseEnrollment.user_id)
        .join(User, CourseEnrollment.user_id == User.id)
        .where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.is_active.is_(True),
            User.role == "student",
        )
    )
    enrolled_result = await session.execute(enrolled_stmt)
    student_ids = [row[0] for row in enrolled_result.all()]

    formatted_time = payload.scheduled_at.strftime("%b %d, %Y at %H:%M UTC")
    for s_id in student_ids:
        notification = InAppNotification(
            user_id=s_id,
            course_id=course_id,
            assessment_id=assessment.id,
            title=f"New Assessment: {payload.title}",
            message=f"{current_user.full_name} scheduled a quiz for {formatted_time} ({payload.duration_minutes}m). Target your practice before the exam.",
            is_read=False,
            notification_type="assessment_scheduled",
        )
        session.add(notification)

    await session.commit()
    await session.refresh(assessment)
    return ScheduledAssessmentResponse.model_validate(assessment)


@router.get(
    "/courses/{course_id}/assessments",
    response_model=list[ScheduledAssessmentResponse],
    summary="List Scheduled Assessments for Course",
)
async def list_course_assessments(
    course_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ScheduledAssessmentResponse]:
    await verify_course_access(course_id, current_user, session)
    stmt = (
        select(ScheduledAssessment)
        .where(ScheduledAssessment.course_id == course_id)
        .order_by(ScheduledAssessment.scheduled_at.asc())
    )
    result = await session.execute(stmt)
    assessments = result.scalars().all()
    return [ScheduledAssessmentResponse.model_validate(a) for a in assessments]


@router.get(
    "/students/{student_id}/notifications",
    response_model=list[InAppNotificationResponse],
    summary="Get Student In-App Notifications",
)
async def get_student_notifications(
    student_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[InAppNotificationResponse]:
    verify_student_ownership(current_user, student_id)
    stmt = (
        select(InAppNotification)
        .where(InAppNotification.user_id == student_id)
        .order_by(InAppNotification.created_at.desc())
    )
    result = await session.execute(stmt)
    notifications = result.scalars().all()
    return [InAppNotificationResponse.model_validate(n) for n in notifications]


@router.post(
    "/students/{student_id}/notifications/{notification_id}/read",
    response_model=InAppNotificationResponse,
    summary="Mark Notification as Read",
)
async def mark_notification_read(
    student_id: str,
    notification_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InAppNotificationResponse:
    verify_student_ownership(current_user, student_id)
    stmt = select(InAppNotification).where(
        InAppNotification.id == notification_id,
        InAppNotification.user_id == student_id,
    )
    result = await session.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notif.is_read = True
    await session.commit()
    await session.refresh(notif)
    return InAppNotificationResponse.model_validate(notif)
