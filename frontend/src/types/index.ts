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

export interface CourseDocumentDetailResponse {
  document: CourseDocumentResponse;
  chunks: DocumentChunkResponse[];
}

export interface RetrievalMatchResponse {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  content: string;
  similarity_score: number;
  token_count: number;
}

export interface RetrievalResponse {
  query: string;
  course_id: string;
  matches_count: number;
  matches: RetrievalMatchResponse[];
}

// --- Mastery & Bounded Diagnosis ---

export interface ObjectiveMasteryResponse {
  objective_id: string;
  objective_code: string;
  mastery_probability: number;
  confidence_bound_lower: number;
  confidence_bound_upper: number;
  attempts_count: number;
  consecutive_correct: number;
  status: "unassessed" | "in_progress" | "mastered";
  last_attempt_at?: string;
}

export interface CourseMasterySummaryResponse {
  student_id: string;
  course_id: string;
  course_mastery_index: number;
  total_objectives: number;
  mastered_count: number;
  in_progress_count: number;
  unassessed_count: number;
  objectives: ObjectiveMasteryResponse[];
}

export interface ObjectiveDiagnosticResponse {
  objective_id: string;
  objective_code: string;
  status: "CONFIRMED_MASTERY" | "CONFIRMED_GAP" | "INSUFFICIENT_EVIDENCE" | "UNTESTED";
  p_mastery: number;
  confidence: number;
  attempts_count: number;
  accuracy: number;
  evidence_rationale: string;
}

export interface CourseDiagnosticSummaryResponse {
  student_id: string;
  course_id: string;
  total_objectives: number;
  confirmed_mastery_count: number;
  confirmed_gap_count: number;
  insufficient_evidence_count: number;
  untested_count: number;
  gap_objective_codes: string[];
  prerequisite_failures: Array<{
    target_code: string;
    unmet_prerequisite_code: string;
  }>;
  objectives: ObjectiveDiagnosticResponse[];
}

export interface DiagnosticSessionPlanResponse {
  student_id: string;
  course_id: string;
  target_objective_id: string;
  planned_questions: Array<{
    question_id: string;
    objective_id: string;
    objective_code: string;
    difficulty: string;
    title: string;
  }>;
  total_questions: number;
  rationale: string;
}

// --- Tutor (SLM Role A) ---

export interface TutorQueryResponse {
  answer: string;
  citations: string[];
  retrieved_chunks_count: number;
  abstention_recommended: boolean;
  model_name?: string;
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
}

// --- Revisor (SLM Role B) ---

export type GroundedAuditStatus =
  | "VERIFIED_GROUNDED"
  | "UNGROUNDED_CLAIM_DETECTED"
  | "DETERMINISTIC_CONTRADICTION"
  | "INSUFFICIENT_EVIDENCE";

export interface RevisorReviewResponse {
  status: GroundedAuditStatus;
  audit_report: string;
  supported_claims: string[];
  unsupported_claims: string[];
  citations: string[];
  retrieved_chunks_count: number;
  deterministic_override_applied: boolean;
  model_name?: string;
  latency_ms?: number;
}

// --- Spaced Retention Scheduling (Rule 6) ---

export interface RetentionItemResponse {
  objective_id: string;
  objective_code: string;
  title: string;
  estimated_retention: number;
  stability_days: number;
  days_since_last_attempt: number;
  review_priority: number;
  is_working_memory_locked: boolean;
  cooldown_remaining_seconds: number;
}

export interface ReviewQueueResponse {
  student_id: string;
  course_id: string;
  total_queue_items: number;
  overdue_items_count: number;
  locked_items_count: number;
  items: RetentionItemResponse[];
}

export interface RetentionSessionPlanResponse {
  student_id: string;
  course_id: string;
  assessment_context: string;
  planned_objectives: string[];
  planned_questions: Array<{
    question_id: string;
    objective_id: string;
    objective_code: string;
    title: string;
    difficulty: string;
  }>;
  total_questions: number;
  rationale: string;
}
