/**
 * Type-safe API Client for Recall Backend.
 */

import {
  AttemptCreate,
  AttemptResponse,
  CourseResponse,
  HealthResponse,
  ProblemDetails,
  QuestionResponse,
  ReadinessResponse,
  TopicResponse,
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  public problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.problem = problem;
  }
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

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
  getHealth: () => fetchApi<HealthResponse>("/healthz"),
  getReadiness: () => fetchApi<ReadinessResponse>("/readyz"),
  listCourses: () => fetchApi<CourseResponse[]>("/courses"),
  getCourseTopics: (courseId: string) => fetchApi<TopicResponse[]>(`/courses/${courseId}/topics`),
  getQuestion: (questionId: string) => fetchApi<QuestionResponse>(`/questions/${questionId}`),
  submitAttempt: (payload: AttemptCreate, idempotencyKey: string) =>
    fetchApi<AttemptResponse>("/attempts", {
      method: "POST",
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify(payload),
    }),
  getAttempt: (attemptId: string) => fetchApi<AttemptResponse>(`/attempts/${attemptId}`),
};
