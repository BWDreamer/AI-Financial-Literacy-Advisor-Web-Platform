import { API_ORIGIN, apiRequest } from "./client";

export type User = {
  id: number;
  email: string;
  username: string | null;
  avatar_url: string | null;
  role: string;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type HeartbeatResponse = {
  last_seen_at: string;
  is_online: boolean;
};

export function registerAccount(email: string, username: string, password: string) {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
}

export function loginAccount(email: string, password: string) {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser() {
  return apiRequest<User>("/auth/me", { authenticated: true });
}

export function sendHeartbeat() {
  return apiRequest<HeartbeatResponse>("/auth/heartbeat", {
    method: "POST",
    authenticated: true,
  });
}

export function updateUsername(username: string) {
  return apiRequest<User>("/auth/me", {
    method: "PUT", authenticated: true, body: JSON.stringify({ username }),
  });
}

export function updateEmail(newEmail: string, currentPassword: string) {
  return apiRequest<User>("/auth/email", {
    method: "PUT", authenticated: true,
    body: JSON.stringify({ new_email: newEmail, current_password: currentPassword }),
  });
}

export function updatePassword(currentPassword: string, newPassword: string) {
  return apiRequest<void>("/auth/password", {
    method: "PUT", authenticated: true,
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export function uploadAvatar(file: File) {
  const body = new FormData();
  body.append("file", file);
  return apiRequest<{ avatar_url: string }>("/auth/avatar", {
    method: "POST", authenticated: true, body,
  });
}

export function avatarUrl(path: string | null) {
  if (!path) return null;
  return /^https?:\/\//.test(path) ? path : `${API_ORIGIN}${path}`;
}
