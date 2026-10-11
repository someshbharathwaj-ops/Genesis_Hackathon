/**
 * Type-safe API Client for Recall Backend with Bearer Authentication.
 * Handles token persistence, error extraction, and full domain API coverage.
 */

import {
  AdminAuditLogEntry,
  AdminAuditSummaryResponse,
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

function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    // Match window hostname (127.0.0.1 or localhost) to prevent IPv4 vs IPv6 resolution stall
    const host = window.location.hostname || "127.0.0.1";
    return `http://${host}:8000/api/v1`;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
}

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

export interface FetchApiOptions extends RequestInit {
  timeoutMs?: number;
}

export async function fetchApi<T>(
  endpoint: string,
  options: FetchApiOptions = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  // Automatically attach Bearer token if present
  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Generous timeouts for local SLM/LLM inference (Ollama phi3:mini), seeding, RAG, and grading
  const isAiEndpoint =
    endpoint.includes("/tutor/") ||
    endpoint.includes("/revisor/") ||
    endpoint.includes("/seed") ||
    endpoint.includes("/attempts") ||
    endpoint.includes("/knowledge/") ||
    endpoint.includes("/documents");
  const defaultTimeout = isAiEndpoint ? 120000 : 30000;
  const timeoutMs = options.timeoutMs ?? defaultTimeout;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: options.signal || controller.signal,
    });
    clearTimeout(timeoutId);

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
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) throw err;
    const isAbort =
      (err instanceof DOMException && err.name === "AbortError") ||
      (err instanceof Error && (err.name === "AbortError" || err.message.toLowerCase().includes("abort")));
    const detailMsg = isAbort
      ? `Request timed out after ${timeoutMs / 1000}s while waiting for AI generation. Local SLM inference may take longer under heavy load.`
      : err instanceof Error
      ? err.message
      : "Network error or timeout";
    throw new ApiError({
      type: "about:blank",
      title: isAbort ? "Request Timeout" : "Network Request Error",
      status: 0,
      detail: detailMsg,
      code: isAbort ? "TIMEOUT" : "NETWORK_ERROR",
      timestamp: new Date().toISOString(),
    });
  }
}

export const recallApi = {
  // Health & Gateway
  getHealth: () => fetchApi<HealthResponse>("/healthz"),
  getReadiness: () => fetchApi<ReadinessResponse>("/readyz"),

  // Authentication & Identity
  login: (email: string, password?: string) =>
    fetchApi<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  demoLogin: (role: "student" | "instructor" | "admin" = "student", courseCode: string = "CS340") =>
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

  // Institutional Administration & Audit
  getAdminAuditSummary: () => fetchApi<AdminAuditSummaryResponse>("/admin/audit-summary"),
  getAdminAuditLogs: (limit: number = 50) =>
    fetchApi<AdminAuditLogEntry[]>(`/admin/audit-logs?limit=${limit}`),
};
