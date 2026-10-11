/**
 * Type-safe API Client for Recall Backend with Bearer Authentication.
 * Handles token persistence, error extraction, and full domain API coverage.
 */

import {
  AttemptCreate,
  AttemptResponse,
  AuthMeResponse,
  CourseDocumentDetailResponse,
  CourseDocumentResponse,
  CourseDiagnosticSummaryResponse,
  CourseMasterySummaryResponse,
  CourseResponse,
  DiagnosticSessionPlanResponse,
  HealthResponse,
  ObjectiveDiagnosticResponse,
  ObjectiveMasteryResponse,
  ProblemDetails,
  QuestionResponse,
  ReadinessResponse,
  RetentionSessionPlanResponse,
  RetrievalResponse,
  ReviewQueueResponse,
  RevisorReviewResponse,
  TokenResponse,
  TopicResponse,
  TutorQueryResponse,
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const TOKEN_STORAGE_KEY = "recall_auth_token";

export class ApiError extends Error {
  public problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.problem = problem;
  }
}

// Token management helpers
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  // Automatically attach Bearer token if present
  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let problem: ProblemDetails;
    try {
      problem = await response.json();
    } catch {
      problem = {
        type: "about:blank",
        title: response.statusText,
        status: response.status,
        detail: `HTTP request failed with status ${response.status}`,
        code: "HTTP_ERROR",
        timestamp: new Date().toISOString(),
      };
    }
    throw new ApiError(problem);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const recallApi = {
  // Health & Gateway
  getHealth: () => fetchApi<HealthResponse>("/healthz"),
  getReadiness: () => fetchApi<ReadinessResponse>("/readyz"),

  // Authentication & Identity
  login: (email: string) =>
    fetchApi<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  demoLogin: (role: "student" | "instructor" = "student", courseCode: string = "CS340") =>
    fetchApi<TokenResponse>("/auth/demo-login", {
      method: "POST",
      body: JSON.stringify({ role, course_code: courseCode }),
    }),
  getMe: () => fetchApi<AuthMeResponse>("/auth/me"),
  enrollUser: (userId: string, courseId: string) =>
    fetchApi<unknown>(`/courses/${courseId}/enroll`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, course_id: courseId }),
    }),

  // Course Catalog & Curriculum
  listCourses: () => fetchApi<CourseResponse[]>("/courses"),
  getCourse: (courseId: string) => fetchApi<CourseResponse>(`/courses/${courseId}`),
  getCourseTopics: (courseId: string) => fetchApi<TopicResponse[]>(`/courses/${courseId}/topics`),
  seedCourse: (courseCode: string) =>
    fetchApi<Record<string, unknown>>(`/courses/seed/${encodeURIComponent(courseCode)}`, {
      method: "POST",
    }),
  seedNewCourse: (payload: { code: string; title?: string; description?: string }) =>
    fetchApi<Record<string, unknown>>("/courses/seed", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  seedDbmsCourse: () =>
    fetchApi<Record<string, unknown>>("/courses/seed/dbms", {
      method: "POST",
    }),
  seedOsCourse: () =>
    fetchApi<Record<string, unknown>>("/courses/seed/os", {
      method: "POST",
    }),

  // Questions
  getQuestion: (questionId: string) => fetchApi<QuestionResponse>(`/questions/${questionId}`),
  listQuestionsForObjective: (objectiveId: string) =>
    fetchApi<QuestionResponse[]>(`/questions/objective/${objectiveId}`),

  // Assessment & Attempts
  submitAttempt: (payload: AttemptCreate, idempotencyKey: string) =>
    fetchApi<AttemptResponse>("/attempts", {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(payload),
    }),
  getAttempt: (attemptId: string) => fetchApi<AttemptResponse>(`/attempts/${attemptId}`),
  listStudentAttempts: (studentId: string) =>
    fetchApi<AttemptResponse[]>(`/attempts/student/${studentId}`),

  // Knowledge Engine & Documents
  uploadDocument: (courseId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchApi<CourseDocumentResponse>(`/courses/${courseId}/documents/upload`, {
      method: "POST",
      body: formData,
    });
  },
  listCourseDocuments: (courseId: string) =>
    fetchApi<CourseDocumentResponse[]>(`/courses/${courseId}/documents`),
  getDocumentDetail: (courseId: string, documentId: string) =>
    fetchApi<CourseDocumentDetailResponse>(`/courses/${courseId}/documents/${documentId}`),
  deleteDocument: (courseId: string, documentId: string) =>
    fetchApi<void>(`/courses/${courseId}/documents/${documentId}`, {
      method: "DELETE",
    }),
  retrieveKnowledge: (courseId: string, query: string, topK: number = 3) =>
    fetchApi<RetrievalResponse>(`/courses/${courseId}/knowledge/retrieve`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),

  // Mastery & Adaptive Engine
  getStudentCourseMastery: (studentId: string, courseId: string) =>
    fetchApi<CourseMasterySummaryResponse>(`/mastery/student/${studentId}/course/${courseId}`),
  getStudentObjectiveMastery: (studentId: string, objectiveId: string) =>
    fetchApi<ObjectiveMasteryResponse>(`/mastery/student/${studentId}/objective/${objectiveId}`),

  // Evidence & Bounded Diagnosis
  getStudentCourseDiagnosis: (studentId: string, courseId: string) =>
    fetchApi<CourseDiagnosticSummaryResponse>(`/diagnosis/student/${studentId}/course/${courseId}`),
  getStudentObjectiveDiagnosis: (studentId: string, objectiveId: string) =>
    fetchApi<ObjectiveDiagnosticResponse>(`/diagnosis/student/${studentId}/objective/${objectiveId}`),
  planDiagnosticSession: (studentId: string, courseId: string, targetObjectiveId: string) =>
    fetchApi<DiagnosticSessionPlanResponse>("/diagnosis/session/plan", {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        course_id: courseId,
        target_objective_id: targetObjectiveId,
      }),
    }),

  // Grounded AI Tutor (SLM Role A)
  askTutor: (courseId: string, studentId: string, query: string, objectiveId?: string) =>
    fetchApi<TutorQueryResponse>(`/courses/${courseId}/tutor/ask`, {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        query,
        objective_id: objectiveId || null,
      }),
    }),

  // Grounded Revisor (SLM Role B)
  reviewExplanation: (
    courseId: string,
    studentId: string,
    candidateText: string,
    queryOrTopic: string = "Course concepts and functional dependencies",
    objectiveId?: string,
    checkDeterministicLogic: boolean = true
  ) => {
    const validQuery =
      queryOrTopic && queryOrTopic.trim().length >= 2
        ? queryOrTopic.trim()
        : "Course concepts and functional dependencies";
    return fetchApi<RevisorReviewResponse>(`/courses/${courseId}/revisor/review`, {
      method: "POST",
      body: JSON.stringify({
        student_id: studentId,
        candidate_text: candidateText,
        query_or_topic: validQuery,
        objective_id: objectiveId || null,
        check_deterministic_logic: checkDeterministicLogic,
      }),
    });
  },

  // Spaced Retention Scheduling (Rule 6)
  getReviewQueue: (courseId: string, studentId: string, cooldownSeconds?: number) => {
    const query = cooldownSeconds !== undefined ? `?cooldown_seconds=${cooldownSeconds}` : "";
    return fetchApi<ReviewQueueResponse>(
      `/courses/${courseId}/scheduling/student/${studentId}/review-queue${query}`
    );
  },
  planRetentionSession: (
    courseId: string,
    studentId: string,
    maxItems: number = 5,
    cooldownSeconds?: number
  ) => {
    const query = cooldownSeconds !== undefined ? `?cooldown_seconds=${cooldownSeconds}` : "";
    return fetchApi<RetentionSessionPlanResponse>(
      `/courses/${courseId}/scheduling/student/${studentId}/plan-session${query}`,
      {
        method: "POST",
        body: JSON.stringify({ max_items: maxItems }),
      }
    );
  },
};
