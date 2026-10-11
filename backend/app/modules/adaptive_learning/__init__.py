"""Adaptive Learning Engine: deterministic grading, mastery estimation,
evidence representation, and bounded curriculum diagnostics.
"""

from app.modules.adaptive_learning.dbms_engine import (
    are_fd_sets_equivalent,
    check_normal_form,
    compute_attribute_closure,
    compute_minimal_cover,
    find_all_candidate_keys,
    is_dependency_preserving,
    is_lossless_join,
)
from app.modules.adaptive_learning.dbms_grader import DBMSDeterministicGrader, GradingOutcome
from app.modules.adaptive_learning.diagnosis_engine import (
    BoundedDiagnosisEngine,
    BoundedDiagnosticOutcome,
    DiagnosticAction,
    DiagnosticStatus,
    EvidenceItem,
    EvidenceLedger,
    EvidenceValidity,
    MisconceptionAnalysis,
    MisconceptionStatus,
    PrerequisiteDiagnosticTrace,
    SufficiencyStatus,
)
from app.modules.adaptive_learning.mastery_engine import (
    MasteryEngine,
    MasteryState,
    ObjectiveMasteryProfile,
)
from app.modules.adaptive_learning.scheduling_engine import (
    RetentionScheduleItem,
    RetentionSessionPlan,
    ReviewUrgency,
    SchedulingEngine,
    SpacedReviewQueue,
)

__all__ = [
    "DBMSDeterministicGrader",
    "GradingOutcome",
    "compute_attribute_closure",
    "find_all_candidate_keys",
    "compute_minimal_cover",
    "check_normal_form",
    "is_lossless_join",
    "is_dependency_preserving",
    "are_fd_sets_equivalent",
    "MasteryEngine",
    "MasteryState",
    "ObjectiveMasteryProfile",
    "BoundedDiagnosisEngine",
    "BoundedDiagnosticOutcome",
    "DiagnosticStatus",
    "DiagnosticAction",
    "EvidenceItem",
    "EvidenceLedger",
    "EvidenceValidity",
    "MisconceptionAnalysis",
    "MisconceptionStatus",
    "PrerequisiteDiagnosticTrace",
    "SufficiencyStatus",
    "SchedulingEngine",
    "RetentionScheduleItem",
    "SpacedReviewQueue",
    "RetentionSessionPlan",
    "ReviewUrgency",
]
