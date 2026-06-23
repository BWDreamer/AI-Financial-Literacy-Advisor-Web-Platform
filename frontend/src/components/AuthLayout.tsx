import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type AuthLayoutProps = {
  activeTab: "login" | "register";
  children: ReactNode;
  subtitle: string;
  title: string;
};

const tabs = [
  { id: "login", label: "Sign In", to: "/login" },
  { id: "register", label: "Create Account", to: "/register" },
] as const;

export default function AuthLayout({ activeTab, children, subtitle, title }: AuthLayoutProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <section className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
        <header className="mb-8 text-center">
          <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-blue-600 text-xl font-bold text-white">F</div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
        </header>
        <nav className="mb-7 grid grid-cols-2 rounded-xl bg-slate-100 p-1" aria-label="Authentication">
          {tabs.map((tab) => (
            <Link key={tab.id} to={tab.to} className={`rounded-lg px-3 py-2 text-center text-sm font-semibold transition ${activeTab === tab.id ? "bg-white text-blue-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
              {tab.label}
            </Link>
          ))}
        </nav>
        {children}
      </section>
    </main>
  );
}
