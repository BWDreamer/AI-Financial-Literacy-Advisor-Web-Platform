import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { avatarUrl } from "../api/auth";
import { archiveGoal, getGoalNotifications, readGoalNotification, type GoalNotification } from "../api/goals";
import { userNavigation } from "../config/userNavigation";
import { useUser } from "../store/UserProvider";
import AppLayout from "./AppLayout";
import BrandMark from "./BrandMark";
import OnboardingOverlay from "./OnboardingOverlay";
import ProfileSettingsModal from "./ProfileSettingsModal";

export default function UserPortalLayout() {
  const { user, loading, error, refreshUser, clearUser } = useUser(); const navigate = useNavigate();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [notices, setNotices] = useState<GoalNotification[]>([]);
  useEffect(() => {
    if (!user) return;
    void loadNotices();
    window.addEventListener("financeai:goals-updated", loadNotices);
    return () => window.removeEventListener("financeai:goals-updated", loadNotices);
  }, [user]);
  if (loading) return <main className="grid min-h-screen place-items-center text-slate-500">Loading your account...</main>;
  if (error && !user) return <main className="grid min-h-screen place-items-center bg-slate-50 p-6"><section className="max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm"><h1 className="text-xl font-bold">Unable to load your account</h1><p className="mt-3 text-sm text-red-600">{error}</p><button onClick={() => void refreshUser()} className="mt-5 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700">Try Again</button></section></main>;
  if (!user) return <Navigate to="/login" replace />;
  function signOut() { clearUser(); navigate("/login", { replace: true }); }
  function openAction(action: string) { if (action === "profile-settings") setSettingsOpen(true); }
  async function loadNotices() {
    try { setNotices(await getGoalNotifications()); } catch { setNotices([]); }
  }
  async function archiveFromNotice(notice: GoalNotification) {
    await archiveGoal(notice.goal_id); await readGoalNotification(notice.id); await loadNotices();
  }
  const unread = notices.some((notice) => !notice.read);
  const showOnboarding = user.role !== "admin" && !user.onboarding_completed;
  return <>
    <AppLayout brand={{ name: "FinanceAI", subtitle: "Your personal advisor", mark: <BrandMark compact /> }} sections={userNavigation}
      brandAction={<NotificationBell open={noticeOpen} notices={notices} unread={unread} onToggle={() => setNoticeOpen((value) => !value)} onArchive={(notice) => void archiveFromNotice(notice)} />}
      profile={{ avatarUrl: avatarUrl(user.avatar_url), name: user.username || user.email, email: user.email }}
      onAction={openAction} onProfileClick={() => setSettingsOpen(true)} onSignOut={signOut} />
    {showOnboarding && <OnboardingOverlay user={user} onFinished={() => void refreshUser()} />}
    {settingsOpen && <ProfileSettingsModal onClose={() => setSettingsOpen(false)} />}
  </>;
}

function NotificationBell({ open, notices, unread, onToggle, onArchive }: {
  open: boolean; notices: GoalNotification[]; unread: boolean;
  onToggle: () => void; onArchive: (notice: GoalNotification) => void;
}) {
  return <div className="relative">
    <button type="button" onClick={onToggle} className="relative grid size-10 place-items-center rounded-xl text-slate-300 hover:bg-slate-800 hover:text-white" aria-label="Goal notifications">
      <Bell size={20} />{unread && <span className="absolute bottom-2 left-2 size-2.5 rounded-full bg-red-500 ring-2 ring-slate-900" />}
    </button>
    {open && <div className="absolute right-0 top-12 z-50 w-72 rounded-2xl bg-white p-3 text-slate-900 shadow-2xl ring-1 ring-slate-200">
      <h3 className="px-2 py-1 text-sm font-bold">Notifications</h3>
      {!notices.length && <p className="px-2 py-3 text-sm text-slate-500">No goal notifications.</p>}
      {notices.map((notice) => <article key={notice.id} className="rounded-xl p-2 hover:bg-slate-50">
        <p className="text-sm font-bold">{notice.title}</p><p className="mt-1 text-xs text-slate-500">{notice.message}</p>
        <button type="button" onClick={() => onArchive(notice)} className="mt-2 text-xs font-bold text-blue-600 hover:text-blue-700">Confirm completed</button>
      </article>)}
    </div>}
  </div>;
}
