import type { LucideIcon } from "lucide-react";

export type NavigationTone = "blue" | "emerald" | "violet" | "amber";

export type NavigationItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  to?: string;
  action?: string;
  tone?: NavigationTone;
};

export type NavigationSection = {
  label: string;
  items: NavigationItem[];
};
