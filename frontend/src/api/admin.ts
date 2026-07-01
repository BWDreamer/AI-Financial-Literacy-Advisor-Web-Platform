import { apiGet, apiRequest } from "./client";

export type AdminUser = {
  id: number;
  user_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  created_at: string;
  is_online: boolean;
  last_seen_at: string | null;
};

export type AdminUserCreate = {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
};

export type AdminUserUpdate = Omit<AdminUserCreate, "password">;

export function getAdminUsers() {
  return apiGet<AdminUser[]>("/admin/users", true);
}

export function inviteAdminUser(request: AdminUserCreate) {
  return apiRequest<AdminUser>("/admin/users", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify(request),
  });
}

export function updateAdminUser(id: number, request: AdminUserUpdate) {
  return apiRequest<AdminUser>(`/admin/users/${id}`, {
    method: "PATCH",
    authenticated: true,
    body: JSON.stringify(request),
  });
}

export function deleteAdminUser(id: number) {
  return apiRequest<void>(`/admin/users/${id}`, {
    method: "DELETE",
    authenticated: true,
  });
}
