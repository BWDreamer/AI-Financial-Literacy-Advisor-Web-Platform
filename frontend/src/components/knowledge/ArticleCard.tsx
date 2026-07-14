import { Bookmark, Eye, Heart } from "lucide-react";
import { Link } from "react-router-dom";
import type { Article } from "../../api/articles";
import { resolveImageUrl } from "../../utils/imageUrl";

type ArticleCardProps = {
  article: Article;
  liked: boolean;
  saved: boolean;
  onToggleLike: (article: Article) => void;
  onToggleSave: (article: Article) => void;
};

function formatDate(value: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-AU", { month: "short", day: "numeric", year: "numeric" });
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-AU", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function metricButtonClass(active: boolean) {
  return [
    "inline-flex items-center gap-1 rounded-full px-2 py-1 transition",
    active ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-50 hover:text-blue-600",
  ].join(" ");
}

export default function ArticleCard({ article, liked, saved, onToggleLike, onToggleSave }: ArticleCardProps) {
  const coverImageUrl = resolveImageUrl(article.coverImageUrl);

  return <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-200 hover:shadow-md">
    <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_11rem]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-500">
          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">{article.category}</span>
          <span>{article.sourceName}</span>
          <span>{formatDate(article.publishedAt)}</span>
        </div>
        <Link to={`/knowledge-hub/${article.id}`} className="mt-3 block text-xl font-bold leading-snug text-slate-950 hover:text-blue-700">
          {article.title}
        </Link>
        <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600">{article.summary}</p>
        <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-500">
          <span>{article.authorName}</span>
          <span className="inline-flex items-center gap-1"><Eye size={15} />{compactNumber(article.views)}</span>
          <button type="button" onClick={() => onToggleLike(article)} className={metricButtonClass(liked)} aria-pressed={liked}>
            <Heart size={15} fill={liked ? "currentColor" : "none"} />{compactNumber(article.likes)}
          </button>
          <button type="button" onClick={() => onToggleSave(article)} className={metricButtonClass(saved)} aria-pressed={saved}>
            <Bookmark size={15} fill={saved ? "currentColor" : "none"} />{compactNumber(article.saves)}
          </button>
        </div>
      </div>
      {coverImageUrl && <Link to={`/knowledge-hub/${article.id}`} aria-label={`Read ${article.title}`}>
        <img src={coverImageUrl} alt={article.title} className="h-36 w-full rounded-xl object-cover sm:h-32" />
      </Link>}
    </div>
  </article>;
}
