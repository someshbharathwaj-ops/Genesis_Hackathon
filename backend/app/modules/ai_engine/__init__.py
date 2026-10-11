"""AI Execution Engine: Replaceable Language Model Providers and Bounded Tutor."""

from app.modules.ai_engine.model_provider import (
    BaseLanguageModelProvider,
    DeterministicMockLanguageModelProvider,
    ModelResponse,
    OllamaLanguageModelProvider,
    get_model_provider,
)
from app.modules.ai_engine.revisor_engine import (
    AssembledRevisorPrompt,
    GroundedAuditStatus,
    RevisorAuditResult,
    RevisorEngine,
)
from app.modules.ai_engine.tutor_engine import (
    AssembledTutorPrompt,
    GroundedTutorEngine,
)

__all__ = [
    "BaseLanguageModelProvider",
    "DeterministicMockLanguageModelProvider",
    "ModelResponse",
    "OllamaLanguageModelProvider",
    "get_model_provider",
    "AssembledTutorPrompt",
    "GroundedTutorEngine",
    "AssembledRevisorPrompt",
    "GroundedAuditStatus",
    "RevisorAuditResult",
    "RevisorEngine",
]
