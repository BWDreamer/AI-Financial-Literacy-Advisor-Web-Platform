import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Bell, Brain, ChevronLeft, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { NavLink, Navigate, useNavigate } from "react-router-dom";
import { avatarUrl } from "../api/auth";
import { archiveGoal, getGoalNotifications, readGoalNotification, type GoalNotification } from "../api/goals";
import type { NavigationItem } from "../config/navigationTypes";
import { userNavigation } from "../config/userNavigation";
import { useUser } from "../store/UserProvider";
import AppLayout from "./AppLayout";
import BrandMark from "./BrandMark";
import OnboardingOverlay from "./OnboardingOverlay";
import ProfileSettingsModal, { AccountTab, SecurityTab, type ProfileSettingsTab } from "./ProfileSettingsModal";
import MemorySettingsPanel from "./MemorySettingsPanel";

export default function UserPortalLayout() {
  const { user, loading, error, refreshUser, clearUser } = useUser(); const navigate = useNavigate();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState<ProfileSettingsTab>("account");
  const [profileOpen, setProfileOpen] = useState(false);
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
  function openSettings(tab: ProfileSettingsTab) { setSettingsTab(tab); setSettingsOpen(true); setProfileOpen(false); }
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
      onAction={openAction} onProfileClick={() => openSettings("account")} onSignOut={signOut}
      mobileNavigation={<MobileUserNavigation profileOpen={profileOpen} setProfileOpen={setProfileOpen} profile={{ avatarUrl: avatarUrl(user.avatar_url), name: user.username || user.email, email: user.email }} notices={notices} unread={unread} noticeOpen={noticeOpen} setNoticeOpen={setNoticeOpen} onArchive={(notice) => void archiveFromNotice(notice)} onSignOut={signOut} />} />
    {showOnboarding && <OnboardingOverlay user={user} onFinished={() => void refreshUser()} />}
    {settingsOpen && <ProfileSettingsModal initialTab={settingsTab} onClose={() => setSettingsOpen(false)} />}
  </>;
}

type MobileProfile = { avatarUrl: string | null; name: string; email: string };

function MobileUserNavigation(props: {
  profileOpen: boolean; setProfileOpen: (open: boolean) => void; profile: MobileProfile;
  notices: GoalNotification[]; unread: boolean; noticeOpen: boolean; setNoticeOpen: (open: boolean) => void;
  onArchive: (notice: GoalNotification) => void; onSignOut: () => void;
}) {
  const [tab, setTab] = useState<ProfileSettingsTab | null>(null);
  return <>
    {props.profileOpen && <MobileProfilePage {...props} tab={tab} setTab={setTab} />}
    <MobileBottomBar items={userNavigation[0].items} profileOpen={props.profileOpen} onNavigate={() => props.setProfileOpen(false)} onProfileClick={() => props.setProfileOpen(true)} />
  </>;
}

function MobileBottomBar({ items, profileOpen, onNavigate, onProfileClick }: { items: NavigationItem[]; profileOpen: boolean; onNavigate: () => void; onProfileClick: () => void }) {
  return <nav className="fixed inset-x-0 bottom-0 z-[70] grid h-[4.75rem] grid-cols-5 items-center border-t border-slate-200 bg-white px-1 lg:hidden" aria-label="Mobile navigation">
    {items.map((item) => <MobileNavItem key={item.id} item={item} profileOpen={profileOpen} onClick={onNavigate} />)}
    <button type="button" onClick={onProfileClick} className={`mx-auto grid size-14 place-items-center transition ${profileOpen ? "text-blue-600" : "text-slate-700 hover:text-blue-600"}`} aria-label="Open user profile"><UserRound size={29} /></button>
  </nav>;
}

function MobileNavItem({ item, profileOpen, onClick }: { item: NavigationItem; profileOpen: boolean; onClick: () => void }) {
  const Icon = item.icon;
  return <NavLink to={item.to || "#"} onClick={onClick} className={({ isActive }) => `mx-auto grid size-14 place-items-center transition ${isActive && !profileOpen ? "text-blue-600" : "text-slate-700 hover:text-blue-600"}`} aria-label={item.label}>
    <Icon size={28} strokeWidth={2} />
  </NavLink>;
}

function MobileProfilePage(props: {
  profile: MobileProfile; notices: GoalNotification[]; unread: boolean; noticeOpen: boolean; setNoticeOpen: (open: boolean) => void;
  onArchive: (notice: GoalNotification) => void; onSignOut: () => void; tab: ProfileSettingsTab | null; setTab: (tab: ProfileSettingsTab | null) => void;
}) {
  return <section className="fixed inset-x-0 top-0 bottom-[4.75rem] z-[60] overflow-y-auto bg-slate-50 lg:hidden">
    {!props.tab && <ProfilePageHeader {...props} />}
    {!props.tab && <div className="space-y-3 px-5 py-5">
      <ProfileAction icon={<UserRound size={24} />} label="Account" onClick={() => props.setTab("account")} />
      <ProfileAction icon={<ShieldCheck size={24} />} label="Security" onClick={() => props.setTab("security")} />
      <ProfileAction icon={<Brain size={24} />} label="Memories" onClick={() => props.setTab("memories")} />
      <ProfileAction icon={<LogOut size={24} />} label="Log out" onClick={props.onSignOut} />
    </div>}
    {props.tab && <MobileProfileDetail tab={props.tab} onBack={() => props.setTab(null)} />}
  </section>;
}

function ProfilePageHeader(props: {
  profile: MobileProfile; notices: GoalNotification[]; unread: boolean; noticeOpen: boolean; setNoticeOpen: (open: boolean) => void; onArchive: (notice: GoalNotification) => void;
}) {
  return <header className="relative flex h-[30svh] min-h-56 max-h-72 flex-col bg-blue-600 px-8 py-5 text-white">
    <h2 className="text-center text-xl font-bold">Profile</h2>
    <div className="absolute right-6 top-6"><NotificationBell open={props.noticeOpen} notices={props.notices} unread={props.unread} onToggle={() => props.setNoticeOpen(!props.noticeOpen)} onArchive={props.onArchive} /></div>
    <div className="flex flex-1 flex-col items-center justify-center gap-2"><ProfilePicture profile={props.profile} /><h3 className="max-w-full truncate text-xl font-bold">{props.profile.name}</h3><p className="max-w-full truncate text-xs text-blue-100">{props.profile.email}</p></div>
  </header>;
}

function ProfilePicture({ profile }: { profile: MobileProfile }) {
  const base = "size-20 rounded-full object-cover ring-4 ring-white/15";
  if (profile.avatarUrl) return <img src={profile.avatarUrl} alt="User avatar" className={base} />;
  return <span className={`${base} grid place-items-center bg-blue-50 text-blue-600`}><UserRound size={40} /></span>;
}

function ProfileAction({ icon, label, onClick }: { icon: ReactNode; label: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="flex w-full items-center gap-4 rounded-2xl bg-white p-3 text-left text-lg font-bold text-slate-900 transition hover:bg-blue-50">
    <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-blue-600 text-white">{icon}</span>{label}
  </button>;
}

function MobileProfileDetail({ tab, onBack }: { tab: ProfileSettingsTab; onBack: () => void }) {
  const title = tab === "account" ? "Account" : tab === "security" ? "Security" : "Memories";
  return <div className="px-4 py-5 pb-8">
    <div className="mb-4 grid grid-cols-[auto_1fr_auto] items-center gap-3">
      <button type="button" onClick={onBack} className="grid size-10 place-items-center rounded-full bg-white text-blue-600 shadow-sm ring-1 ring-slate-200 hover:bg-blue-50" aria-label="Back to profile menu"><ChevronLeft size={22} /></button>
      <h3 className="text-xl font-bold text-slate-950">{title}</h3>
      <span />
    </div>
    {tab === "account" && <AccountTab />}{tab === "security" && <SecurityTab />}{tab === "memories" && <MemorySettingsPanel />}
  </div>;
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
