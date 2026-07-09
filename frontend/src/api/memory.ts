import { apiRequest } from "./client";

export type MemoryCategory =
  | "asset"
  | "debt"
  | "expense"
  | "goal"
  | "income"
  | "preference"
  | "profile"
  | "other";

export type Memory = {
  id: number;
  fact: string;
  category: MemoryCategory;
  source: "chat" | "manual";
  created_at: string;
  updated_at: string;
  last_used_at?: string | null;
};

export type MemoryPayload = {
  fact: string;
  category: MemoryCategory;
};

export type MemoryExport = {
  generated_at: string;
  memories: Memory[];
};

export const getMemories = () =>
  apiRequest<Memory[]>("/memory", { authenticated: true });

export const exportMemories = () =>
  apiRequest<MemoryExport>("/memory/export", { authenticated: true });

export const createMemory = (payload: MemoryPayload) =>
  apiRequest<Memory>("/memory", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify(payload),
  });

export const updateMemory = (id: number, payload: MemoryPayload) =>
  apiRequest<Memory>(`/memory/${id}`, {
    method: "PUT",
    authenticated: true,
    body: JSON.stringify(payload),
  });

export const deleteMemory = (id: number) =>
  apiRequest<void>(`/memory/${id}`, {
    method: "DELETE",
    authenticated: true,
  });
