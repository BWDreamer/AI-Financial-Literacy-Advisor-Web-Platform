import { apiGet, apiRequest } from "./client";
import type { Article, ArticleContentBlocks, ArticleDetail } from "./articles";

export type AdminUser = {
  id: number;
  user_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  avatar_url: string | null;
  role: string;
  region: string | null;
  created_at: string;
  is_online: boolean;
  last_seen_at: string | null;
  goals_count: number;
  liked_articles_count: number;
  saved_articles_count: number;
};

export type AdminUserCreate = {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
};

export type AdminUserUpdate = Omit<AdminUserCreate, "password">;

export type AdvisoryTopicName =
  | "Budgeting"
  | "Saving"
  | "Tax"
  | "Superannuation"
  | "Investing"
  | "Debt";

export type AdvisoryTopicSetting = {
  name: AdvisoryTopicName;
  enabled: boolean;
};

export type AdvisorySettings = {
  topics: AdvisoryTopicSetting[];
};

export function getAdvisorySettings() {
  return apiGet<AdvisorySettings>("/admin/advisory-settings", true);
}

export function updateAdvisorySettings(topics: AdvisoryTopicSetting[]) {
  return apiRequest<AdvisorySettings>("/admin/advisory-settings", {
    method: "PATCH",
    authenticated: true,
    body: JSON.stringify({ topics }),
  });
}

export function getAdminUsers() {
  return apiGet<AdminUser[]>("/admin/users", true);
}

export function getAdminUser(id: number) {
  return apiGet<AdminUser>(`/admin/users/${id}`, true);
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

export type AdminArticleContentBlocks = ArticleContentBlocks;

export type AdminArticleStatus = "draft" | "published" | "archived";

export type AdminArticle = Article & {
  status: AdminArticleStatus;
  updatedAt: string;
};

export type AdminArticleDetail = ArticleDetail & {
  status: AdminArticleStatus;
  updatedAt: string;
};

export type AdminArticlePage = {
  items: AdminArticle[];
  page: number;
  pageSize: number;
  total: number;
};

export type AdminArticleRequest = {
  id?: string;
  title: string;
  summary: string;
  coverImageUrl: string | null;
  authorName: string;
  sourceName: string;
  sourceUrl?: string | null;
  category: string;
  status?: AdminArticleStatus;
  publishedAt?: string | null;
  contentBlocks: AdminArticleContentBlocks;
};

export function getAdminArticles(params: {
  keyword?: string;
  category?: string;
  status?: AdminArticleStatus;
  page?: number;
  pageSize?: number;
} = {}) {
  const query = new URLSearchParams();
  if (params.keyword) query.set("keyword", params.keyword);
  if (params.category && params.category !== "All") query.set("category", params.category);
  if (params.status) query.set("status", params.status);
  query.set("page", String(params.page ?? 1));
  query.set("page_size", String(params.pageSize ?? 100));
  return apiRequest<AdminArticlePage>(`/admin/articles?${query}`, {
    authenticated: true,
  });
}

export function getAdminArticle(id: string) {
  return apiRequest<AdminArticleDetail>(`/admin/articles/${id}`, {
    authenticated: true,
  });
}

export function createAdminArticle(request: Required<Pick<AdminArticleRequest, "id">> & Omit<AdminArticleRequest, "id">) {
  return apiRequest<AdminArticleDetail>("/admin/articles", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify(request),
  });
}

export function updateAdminArticle(id: string, request: AdminArticleRequest) {
  return apiRequest<AdminArticleDetail>(`/admin/articles/${id}`, {
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

export function publishAdminArticle(id: string) {
  return apiRequest<AdminArticleDetail>(`/admin/articles/${id}/publish`, {
    method: "POST",
    authenticated: true,
  });
}

export function unpublishAdminArticle(id: string) {
  return apiRequest<AdminArticleDetail>(`/admin/articles/${id}/unpublish`, {
    method: "POST",
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
