/**
 * Shared API contracts and TypeScript interfaces for Recall.
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

export interface AttemptCreate {
  student_id: string;
  question_id: string;
  submitted_answer: Record<string, unknown>;
  is_hint_assisted?: boolean;
  hint_count?: number;
  time_spent_ms?: number;
  assessment_context?: "diagnostic" | "independent_checkpoint" | "unscored_practice" | "retention_review";
}

export interface AttemptResponse {
  id: string;
  idempotency_key: string;
  student_id: string;
  question_id: string;
  question_version_id: string;
  assessment_context: string;
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
