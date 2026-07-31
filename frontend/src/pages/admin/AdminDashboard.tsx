import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bookmark,
  Eye,
  FileText,
  Heart,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  Users,
  UserPlus,
} from "lucide-react";
import { getAdminUsers, type AdminUser, getPublishedAdminArticles } from "../../api/admin";
import type { Article } from "../../api/articles";

function errorMessage(caught: unknown) {
  return caught instanceof Error ? caught.message : "Something went wrong. Please try again.";
}

function fullName(user: AdminUser) {
  return [user.first_name, user.last_name].filter(Boolean).join(" ") || "Unnamed user";
}

function displayDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-AU", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function MetricCard({
  label,
  value,
  helper,
  icon,
  tone,
}: {
  label: string;
  value: string | number;
  helper: string;
  icon: React.ReactNode;
  tone: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
        </div>
        <span className={`grid size-12 place-items-center rounded-2xl ${tone}`}>{icon}</span>
      </div>
      <p className="mt-4 text-sm text-slate-500">{helper}</p>
    </article>
  );
}

function OnlineStatusChart({ online, offline }: { online: number; offline: number }) {
  const total = online + offline;
  const onlinePercent = total ? Math.round((online / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
      <div
        className="grid size-32 shrink-0 place-items-center rounded-full"
        style={{ background: `conic-gradient(#10b981 0 ${onlinePercent}%, #e2e8f0 ${onlinePercent}% 100%)` }}
        aria-label={`${onlinePercent}% users online`}
      >
        <div className="grid size-20 place-items-center rounded-full bg-white text-center shadow-inner">
          <span className="text-2xl font-bold text-slate-950">{onlinePercent}%</span>
          <span className="-mt-4 text-xs font-semibold text-slate-400">online</span>
        </div>
      </div>
      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex items-center justify-between rounded-xl bg-emerald-50 px-4 py-2.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700"><span className="size-2 rounded-full bg-emerald-500" /> Online</span>
          <strong className="text-slate-950">{online}</strong>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-2.5">
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500"><span className="size-2 rounded-full bg-slate-300" /> Offline</span>
          <strong className="text-slate-950">{offline}</strong>
        </div>
      </div>
    </div>
  );
}

function MonthlyLineChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  const width = 360;
  const height = 140;
  const paddingX = 18;
  const paddingY = 18;
  const usableWidth = width - paddingX * 2;
  const usableHeight = height - paddingY * 2;
  const points = data.map((item, index) => {
    const x = paddingX + (data.length === 1 ? usableWidth / 2 : (index / (data.length - 1)) * usableWidth);
    const y = paddingY + usableHeight - (item.value / max) * usableHeight;
    return { ...item, x, y };
  });
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`).join(" ");

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="New users by month line chart" className="h-40 w-full overflow-visible">
        {[0, 1, 2].map((line) => {
          const y = paddingY + (line / 2) * usableHeight;
          return <line key={line} x1={paddingX} x2={width - paddingX} y1={y} y2={y} stroke="#e2e8f0" strokeWidth="1" />;
        })}
        <path d={path} fill="none" stroke="#6366f1" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="5" fill="#6366f1" stroke="white" strokeWidth="3" />
            <text x={point.x} y={point.y - 12} textAnchor="middle" className="fill-slate-700 text-[11px] font-bold">{point.value}</text>
          </g>
        ))}
      </svg>
      <div className="grid grid-cols-6 gap-2 text-center text-xs font-semibold text-slate-400">
        {data.map((item) => <span key={item.label}>{item.label}</span>)}
      </div>
    </div>
  );
}

function CategoryEngagementChart({ data }: { data: { category: string; engagement: number }[] }) {
  const visibleData = data.length ? data : [{ category: "No articles", engagement: 0 }];
  const max = Math.max(...visibleData.map((item) => item.engagement), 1);

  return (
    <div className="space-y-3">
      {visibleData.map((item) => {
        const width = item.engagement ? Math.max((item.engagement / max) * 100, 8) : 0;
        return (
          <div key={item.category}>
            <div className="mb-2 flex items-center justify-between gap-4 text-sm">
              <span className="font-semibold text-slate-700">{item.category}</span>
              <span className="font-bold text-slate-950">{compactNumber(item.engagement)}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-violet-500" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SectionCard({ title, children, action, className = "" }: { title: string; children: React.ReactNode; action?: React.ReactNode; className?: string }) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <header className="flex items-center justify-between gap-4">
        <h2 className="min-w-0 text-lg font-bold text-slate-950">{title}</h2>
        {action}
      </header>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function TopArticleRow({ label, article, metric }: { label: string; article: Article | null; metric: "views" | "likes" | "saves" }) {
  if (!article) {
    return <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No article data yet.</p>;
  }

  const icons = {
    views: <Eye size={17} className="text-slate-400" />,
    likes: <Heart size={17} className="text-red-500" />,
    saves: <Bookmark size={17} className="text-indigo-500" />,
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-xl bg-slate-50 px-4 py-2.5">
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 truncate font-semibold text-slate-900">{article.title}</p>
      </div>
      <span className="inline-flex shrink-0 items-center gap-2 font-semibold text-slate-700">
        {icons[metric]} {article[metric].toLocaleString()}
      </span>
    </div>
  );
}

function QuickAction({ to, icon, title }: { to: string; icon: React.ReactNode; title: string; description?: string }) {
  return (
    <Link to={to} className="group min-w-0 overflow-hidden rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <span className="grid size-9 place-items-center rounded-lg bg-indigo-50 text-indigo-600">{icon}</span>
        <ArrowRight size={16} className="text-slate-300 transition group-hover:translate-x-1 group-hover:text-indigo-500" />
      </div>
      <h3 className="mt-2 text-sm font-bold text-slate-950">{title}</h3>
    </Link>
  );
}

export default function AdminDashboard() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [adminUsers, articlePage] = await Promise.all([
        getAdminUsers(),
        getPublishedAdminArticles(),
      ]);
      setUsers(adminUsers);
      setArticles(articlePage.items);
      setPageError("");
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const dashboard = useMemo(() => {
    const regularUsers = users.filter((user) => user.role !== "admin");
    const onlineUsers = regularUsers.filter((user) => user.is_online);
    const now = new Date();
    const newThisMonth = regularUsers.filter((user) => {
      const created = new Date(user.created_at);
      return created.getMonth() === now.getMonth() && created.getFullYear() === now.getFullYear();
    });
    const totalViews = articles.reduce((sum, article) => sum + article.views, 0);
    const totalLikes = articles.reduce((sum, article) => sum + article.likes, 0);
    const totalSaves = articles.reduce((sum, article) => sum + article.saves, 0);
    const byViews = [...articles].sort((a, b) => b.views - a.views)[0] ?? null;
    const byLikes = [...articles].sort((a, b) => b.likes - a.likes)[0] ?? null;
    const bySaves = [...articles].sort((a, b) => b.saves - a.saves)[0] ?? null;
    const lastSixMonths = Array.from({ length: 6 }, (_, index) => {
      const date = new Date(now);
      date.setDate(1);
      date.setMonth(now.getMonth() - (5 - index));
      return date;
    });
    const newUsersByMonth = lastSixMonths.map((date) => {
      return {
        label: new Intl.DateTimeFormat("en-AU", { month: "short" }).format(date),
        value: regularUsers.filter((user) => {
          const created = new Date(user.created_at);
          return created.getMonth() === date.getMonth() && created.getFullYear() === date.getFullYear();
        }).length,
      };
    });
    const engagementByCategory = Object.values(articles.reduce<Record<string, { category: string; engagement: number }>>((groups, article) => {
      const category = article.category || "Uncategorised";
      groups[category] ??= { category, engagement: 0 };
      groups[category].engagement += article.views + article.likes + article.saves;
      return groups;
    }, {})).sort((a, b) => b.engagement - a.engagement);
    const recentUsers = [...regularUsers]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5);

    return {
      regularUsers,
      onlineUsers,
      newThisMonth,
      totalViews,
      totalLikes,
      totalSaves,
      totalEngagement: totalViews + totalLikes + totalSaves,
      byViews,
      byLikes,
      bySaves,
      newUsersByMonth,
      engagementByCategory,
      recentUsers,
    };
  }, [articles, users]);

  return (
    <section className="px-5 pb-5 pt-20 sm:p-8 lg:p-12">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-violet-600">Administration</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Dashboard</h1>
        </div>
        <button type="button" onClick={() => void loadDashboard()} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60">
          <RefreshCw size={17} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </header>

      {pageError && (
        <div role="alert" className="mt-6 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between">
          <span>{pageError}</span>
          <button type="button" onClick={() => void loadDashboard()} className="inline-flex items-center gap-2 font-semibold"><RefreshCw size={16} /> Try Again</button>
        </div>
      )}

      <div className="mt-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-2">
        <MetricCard label="Total Users" value={dashboard.regularUsers.length} helper={`${dashboard.newThisMonth.length} joined this month`} icon={<Users size={22} />} tone="bg-blue-50 text-blue-600" />
        <MetricCard label="Published Articles" value={articles.length} helper="Visible in Knowledge Hub" icon={<FileText size={22} />} tone="bg-violet-50 text-violet-600" />
      </div>

      <div className="mt-7 grid items-start gap-7 xl:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div className="order-3 grid min-w-0 gap-7 xl:order-none">
          <SectionCard title="Platform Activity">
            <OnlineStatusChart online={dashboard.onlineUsers.length} offline={Math.max(dashboard.regularUsers.length - dashboard.onlineUsers.length, 0)} />
          </SectionCard>

          <SectionCard title="New Users by Month">
            <MonthlyLineChart data={dashboard.newUsersByMonth} />
          </SectionCard>

          <SectionCard title="Recently Joined Users" action={<Link to="/admin/users" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">View all users</Link>}>
            {loading && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Loading dashboard data...</p>}
            {!loading && dashboard.recentUsers.length === 0 && <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No user data yet.</p>}
            {!loading && dashboard.recentUsers.length > 0 && (
              <div className="divide-y divide-slate-200 overflow-hidden rounded-xl border border-slate-200">
                {dashboard.recentUsers.map((user) => (
                  <div key={user.id} className="grid gap-3 px-4 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-950">{fullName(user)}</p>
                      <p className="truncate text-sm text-slate-500">{user.email}</p>
                      <p className="mt-1 text-xs text-slate-400">Joined {displayDate(user.created_at)}</p>
                    </div>
                    <span className={`w-fit rounded-full px-3 py-1 text-xs font-semibold ${user.is_online ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      {user.is_online ? "Online" : "Offline"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="order-2 grid min-w-0 gap-7 xl:order-none">
          <div className="grid min-w-0 items-stretch gap-7 xl:grid-cols-[minmax(0,1.35fr)_minmax(220px,0.65fr)]">
            <SectionCard title="Content Engagement by Category" className="order-2 h-full xl:order-none">
              <CategoryEngagementChart data={dashboard.engagementByCategory} />
            </SectionCard>

            <SectionCard title="Quick Actions" className="order-1 h-full xl:order-none">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <QuickAction to="/admin/users" icon={<UserPlus size={20} />} title="Invite or manage users" description="Add new users, review details, and manage accounts." />
                <QuickAction to="/admin/settings" icon={<SlidersHorizontal size={20} />} title="Configure advisory topics" description="Enable or disable the topics available to the AI advisor." />
                <QuickAction to="/admin/knowledge" icon={<Plus size={20} />} title="Create a new article" description="Publish Knowledge Hub content for users." />
              </div>
            </SectionCard>
          </div>

          <SectionCard title="Knowledge Hub Performance" action={<Link to="/admin/knowledge" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">Manage articles</Link>}>
            <div className="space-y-3">
              <TopArticleRow label="Most viewed" article={dashboard.byViews} metric="views" />
              <TopArticleRow label="Most liked" article={dashboard.byLikes} metric="likes" />
              <TopArticleRow label="Most saved" article={dashboard.bySaves} metric="saves" />
            </div>
          </SectionCard>
        </div>
      </div>
    </section>
  );
}
