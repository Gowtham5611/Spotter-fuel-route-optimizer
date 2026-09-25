/**
 * API client for the Spotter Fuel Route Optimizer backend.
 *
 * The Vite dev server proxies /api/* to http://localhost:8000,
 * so we use relative paths here for both dev and production.
 */

import type { RouteOptimizeRequest, RouteOptimizeResponse, APIError } from '../types/api';

const API_BASE = '/api/v1';

export class APIClientError extends Error {
  constructor(
    public statusCode: number,
    public errorDetail: string,
    public details?: Record<string, string[]>,
  ) {
    super(errorDetail);
    this.name = 'APIClientError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let errorBody: APIError = { error: `HTTP ${response.status}` };
  try {
    errorBody = await response.json();
  } catch {
    // Ignore JSON parse failure
  }

  throw new APIClientError(
    response.status,
    errorBody.error,
    errorBody.details,
  );
}

export async function optimizeRoute(
  request: RouteOptimizeRequest,
): Promise<RouteOptimizeResponse> {
  const response = await fetch(`${API_BASE}/routes/optimize/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return handleResponse<RouteOptimizeResponse>(response);
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health/`);
  return handleResponse(response);
}
