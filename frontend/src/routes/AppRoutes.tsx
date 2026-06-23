import { Navigate, Route, Routes } from "react-router-dom";
import UserPortalLayout from "../components/UserPortalLayout";
import AdvisorChat from "../pages/AdvisorChat";
import HomePage from "../pages/HomePage";
import KnowledgeHub from "../pages/KnowledgeHub";
import Login from "../pages/Login";
import MyGoals from "../pages/MyGoals";
import Register from "../pages/Register";
import { useUser } from "../store/UserProvider";

function LandingRoute() {
  const { user, loading } = useUser();
  if (loading) return <main className="grid min-h-screen place-items-center text-slate-500">Loading...</main>;
  return <Navigate to={user ? "/home" : "/login"} replace />;
}

export default function AppRoutes() {
  return <Routes>
    <Route path="/" element={<LandingRoute />} />
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route element={<UserPortalLayout />}>
      <Route path="/home" element={<HomePage />} />
      <Route path="/advisor-chat" element={<AdvisorChat />} />
      <Route path="/goals" element={<MyGoals />} />
      <Route path="/knowledge-hub" element={<KnowledgeHub />} />
    </Route>
    <Route path="/dashboard" element={<Navigate to="/home" replace />} />
    <Route path="*" element={<LandingRoute />} />
  </Routes>;
}
