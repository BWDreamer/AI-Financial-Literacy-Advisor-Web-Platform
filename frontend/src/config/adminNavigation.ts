import { BookOpen, LayoutDashboard, SlidersHorizontal, Users } from "lucide-react";
import type { NavigationSection } from "./navigationTypes";

export const adminNavigation: NavigationSection[] = [
  {
    label: "Administration",
    items: [
      { id: "admin-dashboard", label: "Dashboard", icon: LayoutDashboard, to: "/admin/dashboard" },
      { id: "admin-users", label: "User Management", icon: Users, to: "/admin/users" },
      { id: "admin-settings", label: "Advisory Settings", icon: SlidersHorizontal, to: "/admin/settings" },
      { id: "admin-knowledge", label: "Knowledge Hub", icon: BookOpen, to: "/admin/knowledge" },
    ],
  },
];
