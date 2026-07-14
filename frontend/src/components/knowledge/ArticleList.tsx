import type { Article } from "../../api/articles";
import ArticleCard from "./ArticleCard";

type ArticleListProps = {
  articles: Article[];
  likedArticleIds: Set<string>;
  savedArticleIds: Set<string>;
  onToggleLike: (article: Article) => void;
  onToggleSave: (article: Article) => void;
  emptyTitle?: string;
  emptyDescription?: string;
};

export default function ArticleList({
  articles,
  likedArticleIds,
  savedArticleIds,
  onToggleLike,
  onToggleSave,
  emptyTitle = "No articles found",
  emptyDescription = "Try another keyword or category.",
}: ArticleListProps) {
  if (!articles.length) {
    return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
      <p className="font-semibold text-slate-700">{emptyTitle}</p>
      <p className="mt-2 text-sm">{emptyDescription}</p>
    </section>;
  }

  return <section className="space-y-4">
    {articles.map((article) => <ArticleCard
      key={article.id}
      article={article}
      liked={likedArticleIds.has(article.id)}
      saved={savedArticleIds.has(article.id)}
      onToggleLike={onToggleLike}
      onToggleSave={onToggleSave}
    />)}
  </section>;
}
