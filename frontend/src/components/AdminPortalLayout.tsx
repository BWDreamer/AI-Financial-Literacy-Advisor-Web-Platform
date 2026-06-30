import { Bot } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { adminNavigation } from "../config/adminNavigation";
import AppLayout from "./AppLayout";

export default function AdminPortalLayout() {
  const navigate = useNavigate();

  return (
    <AppLayout
      brand={{
        name: "FinAI Advisor",
        subtitle: "Admin Console",
        mark: (
          <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-violet-600 text-white">
            <Bot size={26} aria-hidden="true" />
          </span>
        ),
      }}
      sections={adminNavigation}
      profile={{ avatarUrl: null, name: "Admin User", email: "admin@finai.com" }}
      onAction={() => undefined}
      onProfileClick={() => undefined}
      onSignOut={() => navigate("/login")}
    />
  );
}
