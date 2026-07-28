import { Bot } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { avatarUrl } from "../api/auth";
import { adminNavigation } from "../config/adminNavigation";
import { useUser } from "../store/UserProvider";
import AppLayout from "./AppLayout";

export default function AdminPortalLayout() {
  const navigate = useNavigate();
  const { user, clearUser } = useUser();

  if (!user) return <Navigate to="/login" replace />;

  function signOut() {
    clearUser();
    navigate("/login", { replace: true });
  }

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
      profile={{
        avatarUrl: avatarUrl(user?.avatar_url ?? null),
        name: user?.username || "Admin User",
        email: user?.email || "",
      }}
      onAction={() => undefined}
      onProfileClick={() => undefined}
      onSignOut={signOut}
    />
  );
}
