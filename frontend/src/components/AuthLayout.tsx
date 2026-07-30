import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type AuthLayoutProps = {
  activeTab: "login" | "register";
  children: ReactNode;
  subtitle: string;
  title: string;
};

export default function AuthLayout({ activeTab, children, subtitle, title }: AuthLayoutProps) {
  const switchPrompt =
    activeTab === "login" ? "Don't have an account?" : "Already have an account?";
  const switchLabel = activeTab === "login" ? "Create account" : "Sign in";
  const switchTo = activeTab === "login" ? "/register" : "/login";

  return (
    <main className="relative isolate flex min-h-screen items-center justify-center overflow-hidden bg-slate-950 px-4 py-8 sm:px-6">
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-20 bg-[url('/auth-finance-bg.jpg')] bg-cover bg-center"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-slate-950/70 backdrop-blur-[1px]"
      />
      <section className="grid w-full max-w-6xl gap-10 md:grid-cols-[1fr_0.85fr] md:items-stretch">
        <aside className="hidden md:flex md:flex-col md:pt-20 md:text-white">
          <div className="max-w-2xl">
            <div>
              <p className="mb-5 text-sm font-bold uppercase tracking-[0.42em] text-blue-200/90">
                FinanceAI
              </p>
              <h2 className="max-w-xl bg-gradient-to-r from-white via-blue-100 to-sky-200 bg-clip-text text-6xl font-black leading-[0.95] tracking-[-0.05em] text-transparent drop-shadow-2xl">
                Smarter money decisions start here
              </h2>
              <div className="mt-7 h-1 w-24 rounded-full bg-blue-400/90 shadow-lg shadow-blue-500/40" />
              <p className="mt-7 max-w-lg text-xl font-medium leading-8 text-slate-100 drop-shadow">
                Connect your goals, financial habits, and AI guidance in one calm workspace.
              </p>
            </div>
          </div>
        </aside>

        <div className="flex items-center justify-center px-5 py-8 sm:px-8 md:px-10 md:py-14">
          <div className="w-full max-w-md rounded-[1.75rem] border border-white/25 bg-white/10 p-6 shadow-2xl shadow-slate-950/30 backdrop-blur-xl sm:p-8">
            <header className="mb-8 text-center md:text-left">
              <h1 className="text-4xl font-bold tracking-tight text-white drop-shadow-lg">{title}</h1>
              {subtitle && activeTab === "register" && (
                <p className="mt-2 text-sm leading-6 text-white/75">{subtitle}</p>
              )}
            </header>
            <div className="auth-form-surface">{children}</div>
            <p className="mt-7 text-center text-sm text-white/75">
              {switchPrompt}{" "}
              <Link to={switchTo} className="font-semibold text-white underline underline-offset-4 hover:text-blue-100">
                {switchLabel}
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
