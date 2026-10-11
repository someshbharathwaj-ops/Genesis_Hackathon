"""Grounded Tutor service coordinating course-scoped retrieval and bounded inference."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AssessmentLockoutError, ResourceNotFoundError
from app.modules.ai_engine.model_provider import (
    BaseLanguageModelProvider,
    DeterministicMockLanguageModelProvider,
    get_model_provider,
)
from app.modules.ai_engine.tutor_engine import GroundedTutorEngine
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import UserRepository
from app.schemas.tutor import TutorQueryResponse
from app.services.knowledge_service import KnowledgeService


class TutorService:
    """Service orchestrating course-isolated retrieval and syllabus-grounded tutoring."""

    def __init__(
        self,
        session: AsyncSession,
        knowledge_service: KnowledgeService | None = None,
        model_provider: BaseLanguageModelProvider | None = None,
        course_repo: CourseRepository | None = None,
        user_repo: UserRepository | None = None,
        attempt_repo: AttemptRepository | None = None,
    ):
        self.session = session
        self.knowledge_service = knowledge_service or KnowledgeService(session)
        self.model_provider = model_provider or get_model_provider()
        self.course_repo = course_repo or CourseRepository(session)
        self.user_repo = user_repo or UserRepository(session)
        self.attempt_repo = attempt_repo or AttemptRepository(session)

    async def ask_tutor(
        self,
        course_id: str,
        student_id: str,
        query: str,
        objective_id: str | None = None,
    ) -> TutorQueryResponse:
        """Process student inquiry with server-side lockouts, retrieval, and bounded generation."""
        # 1. Verify course existence
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        # 2. Verify student existence
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        # 3. Non-negotiable architectural rule: Server-Side Scored Assessment Lockout
        active_attempt = await self.attempt_repo.get_active_student_attempt(student_id)
        if active_attempt:
            raise AssessmentLockoutError(student_id=student_id, assessment_id=active_attempt.id)

        # 4. Execute course-scoped semantic retrieval via Knowledge Engine
        retrieval = await self.knowledge_service.retrieve_knowledge(
            course_id=course_id,
            query=query,
            top_k=3,
            similarity_threshold=0.26,
        )

        # 5. Check grounding sufficiency and abstention
        if retrieval.abstention_recommended or not retrieval.matches:
            return TutorQueryResponse(
                answer=GroundedTutorEngine.ABSTENTION_MESSAGE,
                citations=[],
                abstention_recommended=True,
                course_id=course_id,
                student_id=student_id,
                model_used=self.model_provider.model_name,
                retrieved_chunks_count=len(retrieval.matches),
                is_mock=isinstance(self.model_provider, DeterministicMockLanguageModelProvider),
                warning="System abstained due to insufficient or unverified syllabus grounding.",
            )

        # 6. Map matches to RetrievalMatch domain objects for prompt assembler
        matches_domain = [
            RetrievalMatch(
                chunk_id=m.chunk_id,
                document_id=m.document_id,
                document_filename=m.document_filename,
                page_number=m.page_number,
                content=m.content,
                similarity_score=m.similarity_score,
                citation=m.citation,
                metadata_attributes=m.metadata_attributes,
            )
            for m in retrieval.matches
        ]

        # 7. Assemble bounded prompt with strict context limit and citations
        prompt = GroundedTutorEngine.assemble_prompt(
            query=query,
            matches=matches_domain,
        )

        # 8. Generate response using replaceable SLM provider
        model_resp = await self.model_provider.generate_response(
            prompt=prompt.user_prompt,
            system_prompt=prompt.system_prompt,
            temperature=0.2,
        )

        # 9. Return structured pedagogical response without touching grading or mastery state
        warning_msg = (
            "Context was truncated to adhere to safety bounds." if prompt.truncated else None
        )

        return TutorQueryResponse(
            answer=model_resp.text,
            citations=prompt.citations,
            abstention_recommended=False,
            course_id=course_id,
            student_id=student_id,
            model_used=model_resp.model_name,
            retrieved_chunks_count=len(retrieval.matches),
            is_mock=model_resp.is_mock,
            prompt_tokens=model_resp.prompt_tokens,
            completion_tokens=model_resp.completion_tokens,
            warning=warning_msg,
        )
