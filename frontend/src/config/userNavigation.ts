import { BookOpen, Calculator, Goal, Home, Landmark, MessageSquare, Percent, TrendingUp } from "lucide-react";
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
  {
    label: "Quick Tools",
    items: [
      { id: "budget", label: "Budget Calculator", icon: Calculator, action: "budget", tone: "blue" },
      { id: "compound", label: "Compound Interest Calculator", icon: TrendingUp, action: "compound", tone: "emerald" },
      { id: "loan", label: "Loan Repayment Calculator", icon: Landmark, action: "loan", tone: "violet" },
      { id: "tax", label: "Tax Estimator", icon: Percent, action: "tax", tone: "amber" },
    ],
  },
];
