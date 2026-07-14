import { BookOpen, Goal, Home, MessageSquare } from "lucide-react";
import type { NavigationSection } from "./navigationTypes";

export const userNavigation: NavigationSection[] = [
  {
    label: "Menu",
    items: [
      { id: "home", label: "Home Page", icon: Home, to: "/home" },
      { id: "chat", label: "Advisor Chat", icon: MessageSquare, to: "/advisor-chat" },
      { id: "goals", label: "My Goals", icon: Goal, to: "/goals" },
      { id: "knowledge", label: "Knowledge Hub", icon: BookOpen, to: "/knowledge-hub" },
    ],
  },
];
