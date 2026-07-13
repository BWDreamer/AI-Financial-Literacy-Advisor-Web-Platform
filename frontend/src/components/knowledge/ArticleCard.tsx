import { Bookmark, Eye, Heart } from "lucide-react";
import { Link } from "react-router-dom";
import type { Article } from "../../api/articles";
import { resolveImageUrl } from "../../utils/imageUrl";

type ArticleCardProps = {
  article: Article;
};

function formatDate(value: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-AU", { month: "short", day: "numeric", year: "numeric" });
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-AU", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export default function ArticleCard({ article }: ArticleCardProps) {
  const coverImageUrl = resolveImageUrl(article.coverImageUrl);

  return <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-200 hover:shadow-md">
    <Link to={`/knowledge-hub/${article.id}`} className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_11rem]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-500">
          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-blue-700">{article.category}</span>
          <span>{article.sourceName}</span>
          <span>{formatDate(article.publishedAt)}</span>
        </div>
        <h2 className="mt-3 text-xl font-bold leading-snug text-slate-950 hover:text-blue-700">{article.title}</h2>
        <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600">{article.summary}</p>
        <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-500">
          <span>{article.authorName}</span>
          <span className="inline-flex items-center gap-1"><Eye size={15} />{compactNumber(article.views)}</span>
          <span className="inline-flex items-center gap-1"><Heart size={15} />{compactNumber(article.likes)}</span>
          <span className="inline-flex items-center gap-1"><Bookmark size={15} />{compactNumber(article.saves)}</span>
        </div>
      </div>
        {coverImageUrl && <img src={coverImageUrl} alt={article.title} className="h-36 w-full rounded-xl object-cover sm:h-32" />}
    </Link>
  </article>;
}
