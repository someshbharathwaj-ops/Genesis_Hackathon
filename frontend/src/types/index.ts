/**
 * Shared API contracts and TypeScript interfaces for Recall.
 * Strictly mirrors backend Pydantic models across all phases (Phase 0 - Phase 7).
 */

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  code: string;
  timestamp: string;
  invalid_params?: Array<{
    name: string;
    reason: string;
    type: string;
  }>;
}

export interface HealthResponse {
  status: string;
  environment: string;
  version: string;
}

export interface ReadinessResponse {
  status: string;
  engines: Record<string, string>;
}

// --- Identity & Authentication ---

export type UserRole = "student" | "instructor" | "admin";

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface AuthMeResponse {
  user: UserResponse;
  enrolled_course_ids: string[];
}

// --- Curriculum & Catalog ---

export interface CourseResponse {
  id: string;
  code: string;
  title: string;
  description?: string;
  instructor_id?: string;
  created_at: string;
}

export interface LearningObjectiveResponse {
  id: string;
  topic_id: string;
  code: string;
  title: string;
  description: string;
  order_index: number;
  prerequisite_objective_ids: string[];
  metadata_attributes: Record<string, unknown>;
  created_at: string;
}

export interface TopicResponse {
  id: string;
  course_id: string;
  code: string;
  title: string;
  description?: string;
  order_index: number;
  created_at: string;
  objectives: LearningObjectiveResponse[];
}

// --- Questions & Assessment Attempts ---

export interface QuestionVersionResponse {
  id: string;
  question_id: string;
  version_number: number;
  prompt: string;
  difficulty: "introductory" | "intermediate" | "advanced";
  max_score: number;
  options?: Array<Record<string, unknown>>;
  answer_key: Record<string, unknown>;
  rubric: Record<string, unknown>;
  explanation?: string;
  verification_status: "draft" | "verified" | "deprecated";
  verified_by?: string;
  provenance_hash: string;
  created_at: string;
}

export interface QuestionResponse {
  id: string;
  objective_id: string;
  title: string;
  question_type: string;
  is_active: boolean;
  created_at: string;
  versions: QuestionVersionResponse[];
}

export type AssessmentContext =
  | "diagnostic"
  | "independent_checkpoint"
  | "unscored_practice"
  | "retention_review";

export interface AttemptCreate {
  student_id: string;
  question_id: string;
  submitted_answer: Record<string, unknown>;
  is_hint_assisted?: boolean;
  hint_count?: number;
  time_spent_ms?: number;
  assessment_context?: AssessmentContext;
}

export interface AttemptResponse {
  id: string;
  idempotency_key: string;
  student_id: string;
  question_id: string;
  question_version_id: string;
  assessment_context: AssessmentContext;
  submitted_answer: Record<string, unknown>;
  is_hint_assisted: boolean;
  hint_count: number;
  time_spent_ms: number;
  submitted_at?: string;
  status: "in_progress" | "graded" | "regraded" | "rejected_by_student";
  is_correct: boolean;
  score_achieved: number;
  max_possible_score: number;
  grading_provenance: Record<string, unknown>;
  created_at: string;
}

// --- Knowledge Engine & Documents ---

export interface DocumentChunkResponse {
  id: string;
  chunk_index: number;
  page_number: number;
  content: string;
  token_count: number;
  metadata_attributes: Record<string, unknown>;
}

export interface CourseDocumentResponse {
  id: string;
  course_id: string;
  filename: string;
  content_hash: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number;
  status: "pending" | "indexed" | "empty" | "failed";
  error_message?: string;
  created_at: string;
}

export interface CourseDocumentDetailResponse extends Partial<CourseDocumentResponse> {
  document?: CourseDocumentResponse;
  filename?: string;
  chunks: DocumentChunkResponse[];
}

export interface RetrievalMatchResponse {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  filename?: string;
  page_number: number;
  content: string;
  similarity_score: number;
  citation?: string;
  token_count?: number;
  metadata_attributes?: Record<string, unknown>;
}

export interface RetrievalResponse {
  query: string;
  course_id: string;
  total_candidates: number;
  matches_count?: number;
  matches: RetrievalMatchResponse[];
  abstention_recommended?: boolean;
  explanation?: string;
}

// --- Mastery & Bounded Diagnosis ---

export type MasteryState = "mastered" | "developing" | "needs_remediation" | "untested";

export interface ObjectiveMasteryResponse {
  objective_id: string;
  objective_code: string;
  performance_score: number;
  confidence_score: number;
  mastery_state: MasteryState;
  prerequisites_satisfied: boolean;
  blocked_by_prerequisites: string[];
  total_attempts: number;
  distinct_questions_attempted: number;
  unassisted_correct_count: number;
  hint_assisted_count: number;
  details?: Record<string, unknown>;
  // Backward compatibility aliases
  status?: string;
  mastery_probability?: number;
  confidence_bound_lower?: number;
  confidence_bound_upper?: number;
  attempts_count?: number;
  consecutive_correct?: number;
  last_attempt_at?: string;
}

export interface CourseMasterySummaryResponse {
  student_id: string;
  course_id: string;
  total_objectives: number;
  mastered_count: number;
  developing_count: number;
  needs_remediation_count: number;
  untested_count: number;
  average_performance: number;
  average_confidence: number;
  objectives: ObjectiveMasteryResponse[];
  // Backward compatibility alias
  course_mastery_index?: number;
  in_progress_count?: number;
  unassessed_count?: number;
}

export interface ObjectiveDiagnosticResponse {
  objective_id: string;
  objective_code: string;
  diagnostic_status: string;
  performance_score: number;
  confidence_score: number;
  sufficiency_status: string;
  prerequisites_satisfied: boolean;
  root_cause_attribution?: string | null;
  recommended_action: string;
  applied_rules: string[];
  traceable_rationale: string;
  // Backward compatibility
  status?: string;
  p_mastery?: number;
  confidence?: number;
  attempts_count?: number;
  accuracy?: number;
  evidence_rationale?: string;
}

export interface CourseDiagnosticSummaryResponse {
  student_id: string;
  course_id: string;
  total_objectives: number;
  mastered_count: number;
  developing_count: number;
  demonstrated_weakness_count: number;
  insufficient_evidence_count: number;
  untested_count: number;
  conflicting_count: number;
  average_performance: number;
  average_confidence: number;
  identified_root_cause_gaps: string[];
  objectives: ObjectiveDiagnosticResponse[];
  // Backward compatibility aliases
  confirmed_mastery_count?: number;
  confirmed_gap_count?: number;
  gap_objective_codes?: string[];
  prerequisite_failures?: Array<{
    target_code: string;
    unmet_prerequisite_code: string;
  }>;
}

export interface RecommendedQuestionItem {
  question_id: string;
  title: string;
  objective_id: string;
  objective_code: string;
  difficulty: string;
  priority_reason: string;
}

export interface DiagnosticSessionPlanResponse {
  student_id: string;
  course_id: string;
  target_objective_id?: string | null;
  max_session_questions: number;
  recommended_questions: RecommendedQuestionItem[];
  session_rationale: string;
  // Backward compatibility aliases
  planned_questions?: Array<{
    question_id: string;
    objective_id: string;
    objective_code: string;
    difficulty: string;
    title: string;
  }>;
  total_questions?: number;
  rationale?: string;
}

// --- Tutor (SLM Role A) ---

export interface TutorQueryResponse {
  answer: string;
  citations: string[];
  retrieved_chunks_count: number;
  abstention_recommended: boolean;
  course_id: string;
  student_id: string;
  model_used: string;
  is_mock?: boolean;
  latency_ms?: number;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  warning?: string | null;
  // Backward compatibility alias
  model_name?: string;
}

// --- Revisor (SLM Role B) ---

export type GroundedAuditStatus =
  | "verified_grounded"
  | "ungrounded_claim_detected"
  | "contradiction_detected"
  | "insufficient_evidence"
  | "VERIFIED_GROUNDED"
  | "UNGROUNDED_CLAIM_DETECTED"
  | "DETERMINISTIC_CONTRADICTION"
  | "INSUFFICIENT_EVIDENCE";

export interface RevisorReviewResponse {
  course_id: string;
  student_id: string;
  audit_status: GroundedAuditStatus;
  is_approved: boolean;
  summary: string;
  verified_points: string[];
  flagged_issues: string[];
  suggested_revision?: string | null;
  citations_verified: string[];
  abstention_recommended: boolean;
  model_used: string;
  is_mock: boolean;
  retrieved_chunks_count: number;
  deterministic_validation: Record<string, unknown>;
  warning?: string | null;
  // Backward compatibility aliases
  status?: GroundedAuditStatus;
  audit_report?: string;
  supported_claims?: string[];
  unsupported_claims?: string[];
  citations?: string[];
  deterministic_override_applied?: boolean;
  model_name?: string;
  latency_ms?: number;
}

// --- Spaced Retention Scheduling (Rule 6) ---

export interface RetentionItemSchema {
  objective_id: string;
  objective_code: string;
  objective_title: string;
  mastery_state: string;
  performance_score: number;
  confidence_score: number;
  last_attempt_at?: string | null;
  elapsed_hours: number;
  in_working_memory: boolean;
  retention_eligible: boolean;
  interval_days: number;
  next_review_due?: string | null;
  retention_stability_days: number;
  estimated_retention: number;
  urgency_score: number;
  urgency_classification: string;
  recommended_action: string;
  metadata?: Record<string, unknown>;
  // Backward compatibility aliases
  title?: string;
  stability_days?: number;
  days_since_last_attempt?: number;
  review_priority?: number;
  is_working_memory_locked?: boolean;
  cooldown_remaining_seconds?: number;
}

export type RetentionItemResponse = RetentionItemSchema;

export interface ReviewQueueResponse {
  student_id: string;
  course_id: string;
  as_of_time: string;
  total_objectives_evaluated: number;
  overdue_count: number;
  due_count: number;
  working_memory_locked_count: number;
  items: RetentionItemSchema[];
  // Backward compatibility aliases
  total_queue_items?: number;
  overdue_items_count?: number;
  locked_items_count?: number;
}

export interface RetentionSessionPlanResponse {
  student_id: string;
  course_id: string;
  as_of_time: string;
  context: string;
  total_items: number;
  reason: string;
  planned_items: RetentionItemSchema[];
  // Backward compatibility aliases
  assessment_context?: string;
  planned_objectives?: string[];
  planned_questions?: Array<{
    question_id: string;
    objective_id: string;
    objective_code: string;
    title: string;
    difficulty: string;
  }>;
  total_questions?: number;
  rationale?: string;
}

// --- Institutional Administration & Audit ---

export interface CourseAuditBreakdown {
  id: string;
  code: string;
  title: string;
  enrolled_students: number;
  verified_questions: number;
  ingested_chunks: number;
}

export interface AdminAuditSummaryResponse {
  status: string;
  system_telemetry: {
    fastapi_gateway: string;
    database_engine: string;
    environment: string;
    model_provider: string;
    adr_0001_deterministic_grader: string;
    adr_0002_assessment_lockout: string;
  };
  aggregate_counts: {
    total_courses: number;
    total_students: number;
    total_instructors: number;
    verified_questions: number;
    ingested_chunks: number;
  };
  course_summaries: CourseAuditBreakdown[];
}

export interface AdminAuditLogEntry {
  id: string;
  timestamp: string;
  actor: string;
  role: string;
  courseCode: string;
  action: string;
  provenanceHash: string;
  verdict: "VERIFIED" | "REMEDIATION_NEEDED" | "BLOCKED_LOCKOUT" | "GROUNDED" | "CONTRADICTION" | "NEUTRAL";
  details: string;
}
