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
