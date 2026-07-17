import { Navigate, Route, Routes } from "react-router-dom";
import AdminPortalLayout from "../components/AdminPortalLayout";
import UserPortalLayout from "../components/UserPortalLayout";
import AdvisorChat from "../pages/AdvisorChat";
import ArticleDetailPage from "../pages/ArticleDetailPage";
import HomePage from "../pages/HomePage";
import KnowledgeHub from "../pages/KnowledgeHub";
import Login from "../pages/Login";
import MyGoals from "../pages/MyGoals";
import Register from "../pages/Register";
import AdminDashboard from "../pages/admin/AdminDashboard";
import AdminPlaceholder from "../pages/admin/AdminPlaceholder";
import AdminKnowledgeHub from "../pages/admin/KnowledgeHub";
import UserManagement from "../pages/admin/UserManagement";
import { useUser } from "../store/UserProvider";

function LandingRoute() {
  const { user, loading } = useUser();
  if (loading) return <main className="grid min-h-screen place-items-center text-slate-500">Loading...</main>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/home"} replace />;
}

export default function AppRoutes() {
  return <Routes>
    <Route path="/" element={<LandingRoute />} />
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route path="/admin" element={<AdminPortalLayout />}>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<AdminDashboard />} />
      <Route path="users" element={<UserManagement />} />
      <Route path="settings" element={<AdminPlaceholder title="Advisory Settings" />} />
      <Route path="knowledge" element={<AdminKnowledgeHub />} />
    </Route>
    <Route element={<UserPortalLayout />}>
      <Route path="/home" element={<HomePage />} />
      <Route path="/advisor-chat" element={<AdvisorChat />} />
      <Route path="/goals" element={<MyGoals />} />
      <Route path="/knowledge-hub" element={<KnowledgeHub />} />
      <Route path="/knowledge-hub/:articleId" element={<ArticleDetailPage />} />
    </Route>
    <Route path="/dashboard" element={<Navigate to="/home" replace />} />
    <Route path="*" element={<LandingRoute />} />
  </Routes>;
}
