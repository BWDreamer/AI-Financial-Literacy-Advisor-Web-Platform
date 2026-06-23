import { Outlet } from "react-router-dom";
import Sidebar, { SidebarProps } from "./Sidebar";

export default function AppLayout(props: SidebarProps) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar {...props} />
      <main className="min-w-0 flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
