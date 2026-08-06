/**
 * Fetch wrapper for the real Enterprise Copilot Studio backend.
 *
 * Attaches the JWT access token automatically. On a 401, it attempts
 * exactly one silent refresh (via the stored refresh token) and retries
 * the original request; if that also fails, it logs the user out and
 * redirects to /login. Callers never handle token mechanics directly.
 */

import { getAuthState, useAuthStore } from "@/store/auth-store";
import type { TokenResponse } from "@/types/auth";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

// Coalesces concurrent 401s into a single refresh request instead of a
// stampede of parallel /auth/refresh calls (which would race the
// backend's single-use refresh-token rotation and fail all but one).
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken } = getAuthState();
  if (!refreshToken) return null;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) return null;
        const tokens: TokenResponse = await res.json();
        useAuthStore.getState().setTokens(tokens);
        return tokens.access_token;
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function parseErrorBody(res: Response): Promise<{ message: string; detail?: unknown }> {
  try {
    const body = await res.json();
    const message =
      typeof body?.detail === "string" ? body.detail : res.statusText || "Request failed";
    return { message, detail: body };
  } catch {
    return { message: res.statusText || "Request failed" };
  }
}

interface RequestOptions {
  skipAuth?: boolean;
  /** Internal: set to false on the retry-after-refresh pass to avoid looping. */
  allowRetry?: boolean;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { skipAuth = false, allowRetry = true }: RequestOptions = {}
): Promise<T> {
  const { accessToken } = getAuthState();
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;

  const headers: HeadersInit = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(accessToken && !skipAuth ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...init.headers,
  };

  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (res.status === 401 && !skipAuth && allowRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request<T>(path, init, { skipAuth, allowRetry: false });
    }
    useAuthStore.getState().logout();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  if (!res.ok) {
    const { message, detail } = await parseErrorBody(res);
    const error: ApiError = { status: res.status, message, detail };
    throw error;
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, opts?: RequestOptions) => request<T>(path, { method: "GET" }, opts),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(
      path,
      {
        method: "POST",
        body:
          body instanceof FormData
            ? body
            : body !== undefined
              ? JSON.stringify(body)
              : undefined,
      },
      opts
    ),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }, opts),
  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { method: "DELETE" }, opts),
};
