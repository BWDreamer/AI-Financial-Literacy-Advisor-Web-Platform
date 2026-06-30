import { useState } from "react";
import { Menu } from "lucide-react";
import { Outlet } from "react-router-dom";
import Sidebar, { SidebarProps } from "./Sidebar";

export default function AppLayout(props: SidebarProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <button type="button" onClick={() => setSidebarOpen(true)} className="fixed left-4 top-4 z-40 grid size-11 place-items-center rounded-xl bg-slate-900 text-white shadow-lg lg:hidden" aria-label="Open menu"><Menu size={22} /></button>
      {sidebarOpen && <button type="button" onClick={() => setSidebarOpen(false)} className="fixed inset-0 z-40 bg-slate-950/50 lg:hidden" aria-label="Close menu overlay" />}
      <Sidebar {...props} mobileOpen={sidebarOpen} onMobileClose={() => setSidebarOpen(false)} />
      <main className="h-screen min-w-0 flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
