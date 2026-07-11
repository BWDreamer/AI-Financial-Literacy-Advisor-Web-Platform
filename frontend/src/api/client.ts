/// <reference types="vite/client" />

import { getToken } from "../store/tokenService";

function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
  const browserHost = window.location.hostname;

  if (
    configured.includes("localhost:8000")
    && browserHost !== "localhost"
    && browserHost !== "127.0.0.1"
  ) {
    return `http://${browserHost}:8000/api`;
  }

  return configured;
}

export const API_BASE_URL = resolveApiBaseUrl();
export const API_ORIGIN = new URL(API_BASE_URL).origin;

type ApiOptions = RequestInit & { authenticated?: boolean };

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

function errorMessage(detail: unknown) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item?.msg).filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
  return "Something went wrong. Please try again.";
}

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (options.authenticated) {
    const token = getToken();
    if (!token) throw new ApiError("Your session has expired. Please sign in again.", 401);
    headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError("Unable to reach the server. Please try again.", 0);
  }
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(errorMessage(data.detail), response.status);
  return data as T;
}

export function apiGet<T>(path: string, authenticated = false) {
  return apiRequest<T>(path, { authenticated });
}
