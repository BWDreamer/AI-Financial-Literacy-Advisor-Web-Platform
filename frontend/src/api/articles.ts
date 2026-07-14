import { apiRequest } from "./client";
import { getToken } from "../store/tokenService";

export type ArticleCategory = string;
export type ArticleSortBy = "latest" | "most_viewed" | "most_liked" | "most_saved";

export type ArticleContentBlock =
  | {
      type: string;
      text?: string;
      src?: string;
      alt?: string;
      caption?: string;
      attrs?: Record<string, unknown>;
      marks?: ArticleContentMark[];
      content?: ArticleContentBlock[];
    };

export type ArticleContentMark = {
  type: string;
  attrs?: Record<string, unknown>;
};

export type Article = {
  id: string;
  title: string;
  summary: string;
  coverImageUrl: string | null;
  authorName: string;
  sourceName: string;
  publishedAt: string | null;
  category: ArticleCategory;
  views: number;
  likes: number;
  saves: number;
};

export type ArticleDetail = Article & {
  contentBlocks: ArticleContentBlock[];
  likedByMe: boolean;
  savedByMe: boolean;
};

export type ArticlePage = {
  items: Article[];
  page: number;
  pageSize: number;
  total: number;
};

export function getArticles(params: {
  keyword?: string;
  category?: string;
  sortBy?: ArticleSortBy;
  page?: number;
  pageSize?: number;
}) {
  const search = new URLSearchParams();
  if (params.keyword) search.set("keyword", params.keyword);
  if (params.category && params.category !== "All") search.set("category", params.category);
  if (params.sortBy) search.set("sort_by", params.sortBy);
  if (params.page) search.set("page", String(params.page));
  if (params.pageSize) search.set("page_size", String(params.pageSize));
  const query = search.toString();
  return apiRequest<ArticlePage>(`/articles${query ? `?${query}` : ""}`);
}

export function getFeaturedArticles(limit = 5) {
  return apiRequest<Article[]>(`/articles/featured?limit=${limit}`);
}

export function getArticleCategories() {
  return apiRequest<string[]>("/articles/categories");
}

export function getLikedArticleIds() {
  return apiRequest<{ articleIds: string[] }>("/articles/me/liked", { authenticated: true });
}

export function getSavedArticleIds() {
  return apiRequest<{ articleIds: string[] }>("/articles/me/saved", { authenticated: true });
}

export function getArticle(articleId: string) {
  return apiRequest<ArticleDetail>(`/articles/${articleId}`, { authenticated: Boolean(getToken()) });
}

export function incrementArticleViews(articleId: string) {
  return apiRequest<{ articleId: string; views: number }>(`/articles/${articleId}/view`, {
    method: "POST",
    authenticated: true,
  });
}

export function likeArticle(articleId: string) {
  return apiRequest<{ articleId: string; liked: boolean; likes: number }>(`/articles/${articleId}/like`, {
    method: "POST",
    authenticated: true,
  });
}

export function unlikeArticle(articleId: string) {
  return apiRequest<{ articleId: string; liked: boolean; likes: number }>(`/articles/${articleId}/like`, {
    method: "DELETE",
    authenticated: true,
  });
}

export function saveArticle(articleId: string) {
  return apiRequest<{ articleId: string; saved: boolean; saves: number }>(`/articles/${articleId}/save`, {
    method: "POST",
    authenticated: true,
  });
}

export function unsaveArticle(articleId: string) {
  return apiRequest<{ articleId: string; saved: boolean; saves: number }>(`/articles/${articleId}/save`, {
    method: "DELETE",
    authenticated: true,
  });
}
