import { apiGet, apiRequest } from "./client";
import type { Article, ArticleContentBlock, ArticleDetail } from "./articles";

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

export type AdminArticleContentBlock = ArticleContentBlock;

export type AdminArticleRequest = {
  id?: string;
  title: string;
  summary: string;
  coverImageUrl: string | null;
  authorName: string;
  sourceName: string;
  category: string;
  status?: "published";
  publishedAt?: string | null;
  contentBlocks: AdminArticleContentBlock[];
};

export function getPublishedAdminArticles() {
  return apiRequest<{ items: Article[]; page: number; pageSize: number; total: number }>("/articles?page=1&page_size=50&sort_by=latest", {
    authenticated: true,
  });
}

export function getPublishedAdminArticle(id: string) {
  return apiRequest<ArticleDetail>(`/articles/${id}`, {
    authenticated: true,
  });
}

export function createAdminArticle(request: Required<Pick<AdminArticleRequest, "id">> & Omit<AdminArticleRequest, "id">) {
  return apiRequest<ArticleDetail>("/admin/articles", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify(request),
  });
}

export function updateAdminArticle(id: string, request: AdminArticleRequest) {
  return apiRequest<ArticleDetail>(`/admin/articles/${id}`, {
    method: "PUT",
    authenticated: true,
    body: JSON.stringify(request),
  });
}

export function deleteAdminArticle(id: string) {
  return apiRequest<void>(`/admin/articles/${id}`, {
    method: "DELETE",
    authenticated: true,
  });
}

export function uploadAdminArticleImage(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<{ imageUrl: string }>("/admin/articles/images", {
    method: "POST",
    authenticated: true,
    body: formData,
  });
}
