"""Grounded Revisor service coordinating retrieval, adversarial audit, and logic checks."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AssessmentLockoutError, ResourceNotFoundError
from app.modules.ai_engine.model_provider import (
    BaseLanguageModelProvider,
    DeterministicMockLanguageModelProvider,
    get_model_provider,
)
from app.modules.ai_engine.revisor_engine import (
    GroundedAuditStatus,
    RevisorEngine,
)
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import UserRepository
from app.schemas.revisor import RevisorReviewResponse
from app.services.knowledge_service import KnowledgeService


class RevisorService:
    """Service coordinating grounded evidence review and adversarial audit for pedagogical texts."""

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

    async def review_explanation(
        self,
        course_id: str,
        student_id: str,
        candidate_text: str,
        query_or_topic: str,
        objective_id: str | None = None,
        check_deterministic_logic: bool = True,
    ) -> RevisorReviewResponse:
        """Audit a candidate explanation or misconception claim against course materials."""
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

        # 4. Course-scoped semantic retrieval via Knowledge Engine
        retrieval = await self.knowledge_service.retrieve_knowledge(
            course_id=course_id,
            query=query_or_topic,
            top_k=3,
            similarity_threshold=0.26,
        )

        # 5. Check grounding sufficiency and abstention
        if retrieval.abstention_recommended or not retrieval.matches:
            return RevisorReviewResponse(
                course_id=course_id,
                student_id=student_id,
                audit_status=GroundedAuditStatus.INSUFFICIENT_EVIDENCE,
                is_approved=False,
                summary=RevisorEngine.ABSTENTION_MESSAGE,
                verified_points=[],
                flagged_issues=["Insufficient syllabus evidence to audit candidate text."],
                suggested_revision=None,
                citations_verified=[],
                abstention_recommended=True,
                model_used=self.model_provider.model_name,
                is_mock=isinstance(self.model_provider, DeterministicMockLanguageModelProvider),
                retrieved_chunks_count=len(retrieval.matches),
                deterministic_validation={},
                warning="System abstained due to insufficient course excerpts.",
            )

        # 6. Optional deterministic validation check (relational closure / normal forms)
        det_checks = {}
        if check_deterministic_logic:
            det_checks = RevisorEngine.verify_deterministic_claims(candidate_text)

        # 7. Map matches to RetrievalMatch domain objects
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

        # 8. Enrich topic with Curriculum DAG objective & prerequisite chain if objective_id supplied
        effective_topic = query_or_topic
        if objective_id:
            from app.repositories.course_repo import LearningObjectiveRepository

            lo_repo = LearningObjectiveRepository(self.session)
            lo = await lo_repo.get_by_id(objective_id)
            if lo:
                prereqs = (
                    f"Prerequisites: {', '.join(lo.prerequisite_objective_ids)}"
                    if lo.prerequisite_objective_ids
                    else "Foundational node (no prerequisites)"
                )
                effective_topic = (
                    f"{query_or_topic}\n[Curriculum DAG Context: Objective '{lo.title}' ({lo.code}) | {prereqs}]"
                )

        # 9. Assemble bounded Revisor prompt
        prompt = RevisorEngine.assemble_prompt(
            candidate_text=candidate_text,
            query_or_topic=effective_topic,
            matches=matches_domain,
        )

        # 10. Execute bounded SLM inference
        model_resp = await self.model_provider.generate_response(
            prompt=prompt.user_prompt,
            system_prompt=prompt.system_prompt,
            temperature=0.1,
        )

        # 10. Parse and cross-examine findings
        audit_result = RevisorEngine.parse_model_output(
            model_text=model_resp.text,
            citations=prompt.citations,
            deterministic_checks=det_checks,
        )

        warning_msg = (
            "Context was truncated to adhere to safety bounds." if prompt.truncated else None
        )

        return RevisorReviewResponse(
            course_id=course_id,
            student_id=student_id,
            audit_status=audit_result.audit_status,
            is_approved=audit_result.is_approved,
            summary=audit_result.summary,
            verified_points=audit_result.verified_points,
            flagged_issues=audit_result.flagged_issues,
            suggested_revision=audit_result.suggested_revision,
            citations_verified=audit_result.citations_verified,
            abstention_recommended=audit_result.abstention_recommended,
            model_used=model_resp.model_name,
            is_mock=model_resp.is_mock,
            retrieved_chunks_count=len(retrieval.matches),
            deterministic_validation=audit_result.deterministic_checks,
            warning=warning_msg,
        )
