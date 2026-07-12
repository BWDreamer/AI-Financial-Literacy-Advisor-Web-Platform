import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { Link } from "react-router-dom";
import ArticleList from "../components/knowledge/ArticleList";
import {
  getArticleCategories,
  getArticles,
  getFeaturedArticles,
  getLikedArticleIds,
  getSavedArticleIds,
  type Article,
  type ArticleSortBy,
} from "../api/articles";
import { ApiError } from "../api/client";
import { resolveImageUrl } from "../utils/imageUrl";

type KnowledgeTab = "all" | "saved" | "liked";

const knowledgeTabs: { id: KnowledgeTab; label: string }[] = [
  { id: "all", label: "All Articles" },
  { id: "saved", label: "Saved" },
  { id: "liked", label: "Liked" },
];

const sortOptions: { id: ArticleSortBy; label: string }[] = [
  { id: "latest", label: "Latest" },
  { id: "most_viewed", label: "Most Viewed" },
  { id: "most_liked", label: "Most Liked" },
  { id: "most_saved", label: "Most Saved" },
];

function formatDate(value: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-AU", { month: "long", day: "numeric", year: "numeric" });
}

function emptyStateForTab(tab: KnowledgeTab) {
  if (tab === "saved") return { title: "No saved articles yet.", description: "Save articles from the article detail page and they will appear here." };
  if (tab === "liked") return { title: "No liked articles yet.", description: "Like articles from the article detail page and they will appear here." };
  return { title: "No articles found", description: "Try another keyword, category or sort option." };
}

function ArticlePersonalTabs({ selectedTab, onChange }: { selectedTab: KnowledgeTab; onChange: (tab: KnowledgeTab) => void }) {
  return <div className="inline-flex rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm" role="tablist" aria-label="Knowledge article views">
    {knowledgeTabs.map((tab) => {
      const active = selectedTab === tab.id;
      return <button
        key={tab.id}
        type="button"
        onClick={() => onChange(tab.id)}
        className={[
          "rounded-xl px-4 py-2.5 text-sm font-bold transition sm:px-5",
          active ? "bg-blue-600 text-white shadow-sm shadow-blue-200" : "text-slate-700 hover:bg-slate-50 hover:text-blue-600",
        ].join(" ")}
      >
        {tab.label}
      </button>;
    })}
  </div>;
}

function ArticleSortControl({ sortBy, onChange }: { sortBy: ArticleSortBy; onChange: (sortBy: ArticleSortBy) => void }) {
  const [open, setOpen] = useState(false);
  const selectedLabel = sortOptions.find((option) => option.id === sortBy)?.label || "Latest";

  function chooseSort(nextSortBy: ArticleSortBy) {
    onChange(nextSortBy);
    setOpen(false);
  }

  return <div className="relative w-full sm:w-auto">
    <button
      type="button"
      onClick={() => setOpen((current) => !current)}
      className="flex w-full items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm hover:border-blue-200 sm:w-auto"
    >
      <span className="font-semibold">Sort by</span>
      <span className="flex items-center gap-2 font-bold text-slate-900">
        {selectedLabel}
        <ChevronDown size={16} className={open ? "rotate-180 transition" : "transition"} />
      </span>
    </button>

    {open && <div className="absolute right-0 z-20 mt-2 w-full overflow-hidden rounded-2xl border border-slate-200 bg-white p-1 shadow-xl shadow-slate-200/70 sm:w-48">
      {sortOptions.map((option) => {
        const active = option.id === sortBy;
        return <button
          key={option.id}
          type="button"
          onClick={() => chooseSort(option.id)}
          className={[
            "w-full rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition",
            active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50 hover:text-blue-600",
          ].join(" ")}
        >
          {option.label}
        </button>;
      })}
    </div>}
  </div>;
}

function ArticleCategoryChips({ categories, selectedCategory, onChange }: { categories: string[]; selectedCategory: string; onChange: (category: string) => void }) {
  return <nav className="-mx-4 mt-4 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0" aria-label="Article categories">
    <div className="flex min-w-max gap-2">
      {["All", ...categories].map((category) => {
        const active = selectedCategory === category;
        return <button
          key={category}
          type="button"
          onClick={() => onChange(category)}
          className={[
            "shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-semibold transition",
            active ? "border-blue-600 bg-blue-600 text-white shadow-sm shadow-blue-100" : "border-slate-200 bg-white text-slate-600 hover:border-blue-200 hover:text-blue-600",
          ].join(" ")}
        >
          {category}
        </button>;
      })}
    </div>
  </nav>;
}

function FeaturedHero({ featuredArticles }: { featuredArticles: Article[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const activeArticle = featuredArticles[activeIndex] || featuredArticles[0];

  useEffect(() => {
    if (featuredArticles.length < 2) return undefined;
    const timer = window.setInterval(() => {
      setActiveIndex((currentIndex) => (currentIndex + 1) % featuredArticles.length);
    }, 5500);
    return () => window.clearInterval(timer);
  }, [featuredArticles.length]);

  if (!activeArticle) return null;

  return <header className="relative overflow-hidden rounded-[2rem] bg-slate-950 shadow-xl shadow-slate-300/60">
    <div className="absolute inset-0">
      {featuredArticles.map((article, index) => {
        const coverImageUrl = resolveImageUrl(article.coverImageUrl);
        return coverImageUrl && <img
          key={article.id}
          src={coverImageUrl}
          alt=""
          className={[
            "absolute inset-0 h-full w-full object-cover transition-opacity duration-700",
            index === activeIndex ? "opacity-100" : "opacity-0",
          ].join(" ")}
        />;
      })}
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/80 to-slate-950/20" />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-slate-950/40" />
    </div>

    <div className="relative grid min-h-[13rem] gap-5 p-4 text-white sm:p-5 lg:grid-cols-[minmax(0,1fr)_16rem] lg:p-6">
      <div className="flex max-w-3xl flex-col justify-between gap-4">
        <p className="text-sm font-bold uppercase tracking-[0.22em] text-blue-200">Daily Knowledge Mix</p>
        <section className="max-w-2xl">
          <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-blue-100">
            <span className="rounded-full bg-blue-500 px-3 py-1 text-white">{activeArticle.category}</span>
            <span>{activeArticle.sourceName}</span>
            <span>{formatDate(activeArticle.publishedAt)}</span>
          </div>
          <Link to={`/knowledge-hub/${activeArticle.id}`} className="mt-3 block text-2xl font-black leading-tight tracking-tight text-white hover:text-blue-200 sm:text-3xl">{activeArticle.title}</Link>
          <p className="mt-2 line-clamp-2 max-w-xl text-sm leading-6 text-slate-200">{activeArticle.summary}</p>
        </section>
      </div>

      <aside className="hidden self-end rounded-2xl border border-white/15 bg-white/10 p-2 backdrop-blur md:block">
        <p className="px-2 pb-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-300">Today&apos;s 5</p>
        <div className="space-y-2">
          {featuredArticles.map((article, index) => <button
            key={article.id}
            type="button"
            onClick={() => setActiveIndex(index)}
            className={[
              "w-full rounded-xl p-2 text-left transition",
              index === activeIndex ? "bg-white text-slate-950" : "text-white hover:bg-white/10",
            ].join(" ")}
          >
            <p className="line-clamp-1 text-xs font-bold leading-5">{article.title}</p>
            <p className={index === activeIndex ? "mt-1 text-xs text-slate-500" : "mt-1 text-xs text-slate-300"}>{article.category}</p>
          </button>)}
        </div>
      </aside>
    </div>
  </header>;
}

export default function KnowledgeBasePage() {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedTab, setSelectedTab] = useState<KnowledgeTab>("all");
  const [sortBy, setSortBy] = useState<ArticleSortBy>("latest");
  const [articles, setArticles] = useState<Article[]>([]);
  const [featuredArticles, setFeaturedArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [likedArticleIds, setLikedArticleIds] = useState<Set<string>>(new Set());
  const [savedArticleIds, setSavedArticleIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    Promise.all([
      getArticles({ keyword: query.trim(), category: selectedCategory, sortBy, page: 1, pageSize: 50 }),
      getFeaturedArticles(5),
      getArticleCategories(),
    ])
      .then(([articlePage, featured, categoryList]) => {
        if (!active) return;
        setArticles(articlePage.items);
        setFeaturedArticles(featured);
        setCategories(categoryList);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Unable to load articles.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [query, selectedCategory, sortBy]);

  useEffect(() => {
    let active = true;
    Promise.all([getLikedArticleIds(), getSavedArticleIds()])
      .then(([liked, saved]) => {
        if (!active) return;
        setLikedArticleIds(new Set(liked.articleIds));
        setSavedArticleIds(new Set(saved.articleIds));
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) return;
        console.error(err);
      });

    return () => {
      active = false;
    };
  }, []);

  const visibleArticles = useMemo(() => {
    if (selectedTab === "saved") return articles.filter((article) => savedArticleIds.has(article.id));
    if (selectedTab === "liked") return articles.filter((article) => likedArticleIds.has(article.id));
    return articles;
  }, [articles, likedArticleIds, savedArticleIds, selectedTab]);

  const emptyState = emptyStateForTab(selectedTab);

  return <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
    <section className="mx-auto max-w-6xl">
      <FeaturedHero featuredArticles={featuredArticles} />

      <div className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1fr)_26rem] lg:items-end">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-blue-600">Latest Articles</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">Explore the full knowledge base</h2>
        </div>
        <label className="rounded-full border border-slate-200 bg-white px-4 py-3 text-slate-500 shadow-sm focus-within:border-blue-300 focus-within:ring-4 focus-within:ring-blue-100">
          <span className="flex items-center gap-3">
            <Search size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full bg-transparent text-sm text-slate-900 outline-none"
              placeholder="Search articles"
            />
            {query && <button type="button" onClick={() => setQuery("")} className="text-xs font-bold text-blue-600 hover:text-blue-700">
              Clear
            </button>}
          </span>
        </label>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <ArticlePersonalTabs selectedTab={selectedTab} onChange={setSelectedTab} />
        <ArticleSortControl sortBy={sortBy} onChange={setSortBy} />
      </div>

      <ArticleCategoryChips categories={categories} selectedCategory={selectedCategory} onChange={setSelectedCategory} />

      <div className="mt-5">
        {loading && <section className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">Loading articles...</section>}
        {!loading && error && <section className="rounded-2xl border border-red-100 bg-red-50 p-8 text-center text-red-600">{error}</section>}
        {!loading && !error && <ArticleList articles={visibleArticles} emptyTitle={emptyState.title} emptyDescription={emptyState.description} />}
      </div>
    </section>
  </main>;
}
