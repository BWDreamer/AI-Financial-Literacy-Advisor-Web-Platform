import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { avatarUrl } from "../api/auth";
import { userNavigation } from "../config/userNavigation";
import { useUser } from "../store/UserProvider";
import AppLayout from "./AppLayout";
import BrandMark from "./BrandMark";
import CalculatorModal, { CalculatorType } from "./CalculatorModal";
import ProfileSettingsModal from "./ProfileSettingsModal";

const calculatorTypes: CalculatorType[] = ["budget", "compound", "loan", "tax"];
const isCalculator = (action: string): action is CalculatorType => calculatorTypes.includes(action as CalculatorType);

export default function UserPortalLayout() {
  const { user, loading, error, refreshUser, clearUser } = useUser(); const navigate = useNavigate();
  const [calculator, setCalculator] = useState<CalculatorType | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  if (loading) return <main className="grid min-h-screen place-items-center text-slate-500">Loading your account...</main>;
  if (error && !user) return <main className="grid min-h-screen place-items-center bg-slate-50 p-6"><section className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm"><h1 className="text-xl font-bold">Unable to load your account</h1><p className="mt-3 text-sm text-red-600">{error}</p><button onClick={() => void refreshUser()} className="mt-5 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700">Try Again</button></section></main>;
  if (!user) return <Navigate to="/login" replace />;
  function signOut() { clearUser(); navigate("/login", { replace: true }); }
  function openAction(action: string) { if (isCalculator(action)) setCalculator(action); }
  return <>
    <AppLayout brand={{ name: "FinanceAI", subtitle: "Your personal advisor", mark: <BrandMark compact /> }} sections={userNavigation}
      profile={{ avatarUrl: avatarUrl(user.avatar_url), name: user.username || user.email, email: user.email }}
      onAction={openAction} onProfileClick={() => setSettingsOpen(true)} onSignOut={signOut} />
    {calculator && <CalculatorModal type={calculator} onClose={() => setCalculator(null)} />}
    {settingsOpen && <ProfileSettingsModal onClose={() => setSettingsOpen(false)} />}
  </>;
}
