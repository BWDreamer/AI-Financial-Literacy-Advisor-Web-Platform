import { API_ORIGIN } from "../api/client";

export function resolveImageUrl(value: string | null) {
  if (!value) return null;
  if (/^https?:\/\//i.test(value) || value.startsWith("data:")) return value;
  return `${API_ORIGIN}${value}`;
}
