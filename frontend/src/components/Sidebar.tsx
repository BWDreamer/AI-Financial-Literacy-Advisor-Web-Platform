import type { ReactNode } from "react";
import { LogOut, UserRound } from "lucide-react";
import { NavLink } from "react-router-dom";
import type { NavigationItem, NavigationSection, NavigationTone } from "../config/navigationTypes";

export type SidebarProfile = { avatarUrl: string | null; name: string; email: string };
export type SidebarProps = {
  brand: { name: string; subtitle: string; mark: ReactNode };
  sections: NavigationSection[];
  profile: SidebarProfile;
  onAction: (action: string) => void;
  onProfileClick: () => void;
  onSignOut: () => void;
};

const baseItem = "group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition";
const tones: Record<NavigationTone, string> = {
  blue: "bg-blue-500/15 text-blue-400",
  emerald: "bg-emerald-500/15 text-emerald-400",
  violet: "bg-violet-500/15 text-violet-400",
  amber: "bg-amber-500/15 text-amber-400",
};

function ItemIcon({ item, active = false }: { item: NavigationItem; active?: boolean }) {
  const Icon = item.icon; const tone = item.tone ? tones[item.tone] : "text-slate-400";
  return <span className={`grid size-8 shrink-0 place-items-center rounded-lg transition ${active ? "bg-blue-500/20 text-blue-300" : tone}`}>
    <Icon size={18} strokeWidth={1.9} aria-hidden="true" />
  </span>;
}

function SidebarItem({ item, onAction }: { item: NavigationItem; onAction: (action: string) => void }) {
  if (item.to) return <NavLink to={item.to} className={({ isActive }) => `${baseItem} ${isActive ? "bg-slate-700/80 text-white ring-1 ring-inset ring-blue-400/80 shadow-sm" : "text-slate-300 hover:bg-slate-800 hover:text-white"}`}>
    {({ isActive }) => <><ItemIcon item={item} active={isActive} /><span className="min-w-0 flex-1 truncate">{item.label}</span>{isActive && <span className="size-2 rounded-full bg-blue-400" />}</>}
  </NavLink>;
  return <button type="button" onClick={() => item.action && onAction(item.action)} className={`${baseItem} text-slate-300 hover:bg-slate-800 hover:text-white`}>
    <ItemIcon item={item} /><span className="min-w-0 flex-1 truncate">{item.label}</span>
  </button>;
}

function ProfileAvatar({ profile }: { profile: SidebarProfile }) {
  if (profile.avatarUrl) return <img src={profile.avatarUrl} alt="User avatar" className="size-11 rounded-full object-cover ring-2 ring-blue-400/30" />;
  return <span className="grid size-11 place-items-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-400 text-white"><UserRound size={22} /></span>;
}

export default function Sidebar({ brand, sections, profile, onAction, onProfileClick, onSignOut }: SidebarProps) {
  return <aside className="flex min-h-screen w-80 shrink-0 flex-col border-r border-slate-700 bg-slate-900 text-white shadow-xl shadow-slate-950/10">
    <header className="flex items-center gap-3 px-6 py-6">{brand.mark}<div className="min-w-0"><p className="truncate text-lg font-bold tracking-tight">{brand.name}</p><p className="truncate text-sm text-slate-400">{brand.subtitle}</p></div></header>
    <nav className="flex-1 overflow-y-auto" aria-label="Portal navigation">{sections.map((section) => <section key={section.label} className="border-t border-slate-700/80 px-4 py-6">
      <h2 className="mb-3 px-3 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{section.label}</h2>
      <div className="space-y-1.5">{section.items.map((item) => <SidebarItem key={item.id} item={item} onAction={onAction} />)}</div>
    </section>)}</nav>
    <footer className="border-t border-slate-700 p-4"><button type="button" onClick={onProfileClick} className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-slate-800">
      <ProfileAvatar profile={profile} /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{profile.name}</span><span className="block truncate text-xs text-slate-400">{profile.email}</span></span><span className="size-2.5 rounded-full bg-emerald-400 ring-4 ring-emerald-400/10" />
    </button><button type="button" onClick={onSignOut} className="mt-3 flex w-full items-center gap-3 rounded-xl border border-slate-700 px-4 py-3 text-sm font-medium text-slate-400 transition hover:border-slate-600 hover:bg-slate-800 hover:text-white"><LogOut size={18} />Sign Out</button></footer>
  </aside>;
}
