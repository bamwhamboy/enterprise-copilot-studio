import { API_BASE_URL, apiClient } from "@/services/api-client";
import type { AuthUser, LoginPayload, RegisterPayload, TokenResponse } from "@/types/auth";

/**
 * Login uses application/x-www-form-urlencoded (OAuth2PasswordRequestForm
 * on the backend, not JSON) -- this is what makes Swagger's "Authorize"
 * button work natively there, so the frontend speaks the same wire
 * format rather than adding a second login contract. Handled as a raw
 * fetch (not apiClient) since it needs neither an auth header nor JSON
 * body encoding.
 */
export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const body = new URLSearchParams();
  body.set("username", payload.email);
  body.set("password", payload.password);

  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    let message = "Incorrect email or password.";
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") message = data.detail;
    } catch {
      // fall back to default message
    }
    throw { status: res.status, message };
  }

  return res.json();
}

export function register(payload: RegisterPayload): Promise<AuthUser> {
  return apiClient.post<AuthUser>("/auth/register", payload, { skipAuth: true });
}

export function fetchCurrentUser(): Promise<AuthUser> {
  return apiClient.get<AuthUser>("/users/me");
}

export function logoutRequest(refreshToken: string): Promise<void> {
  return apiClient.post<void>(
    "/auth/logout",
    { refresh_token: refreshToken },
    { skipAuth: true }
  );
}
