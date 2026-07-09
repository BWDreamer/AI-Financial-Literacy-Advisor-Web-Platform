import { ArrowLeft, Bookmark, Eye, Heart } from "lucide-react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useState } from "react";
import { findArticleById, type ArticleContentBlock } from "../data/articlesMock";
import { getLikedArticleIds, getSavedArticleIds, toggleLikedArticle, toggleSavedArticle } from "../utils/articleEngagement";

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("en-AU", { month: "long", day: "numeric", year: "numeric" });
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-AU", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function ArticleContentBlockView({ block }: { block: ArticleContentBlock }) {
  if (block.type === "paragraph") {
    return <p>{block.text}</p>;
  }

  return <figure className="my-8">
    <img src={block.src} alt={block.alt} className="mx-auto h-56 w-full max-w-xl rounded-2xl object-cover sm:h-64" />
    {block.caption && <figcaption className="mt-3 text-center text-sm leading-6 text-slate-500">{block.caption}</figcaption>}
  </figure>;
}

function actionClass(active: boolean) {
  return [
    "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-sm font-medium transition",
    active ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-50 hover:text-blue-600",
  ].join(" ");
}

export default function ArticleDetailPage() {
  const { articleId } = useParams();
  const article = findArticleById(articleId);
  const [likedArticleIds, setLikedArticleIds] = useState(() => getLikedArticleIds());
  const [savedArticleIds, setSavedArticleIds] = useState(() => getSavedArticleIds());

  if (!article) return <Navigate to="/knowledge-hub" replace />;
  const currentArticle = article;

  const liked = likedArticleIds.has(currentArticle.id);
  const saved = savedArticleIds.has(currentArticle.id);
  const displayedLikes = currentArticle.likes + (liked ? 1 : 0);
  const displayedSaves = currentArticle.saves + (saved ? 1 : 0);

  function handleLike() {
    setLikedArticleIds(new Set(toggleLikedArticle(currentArticle.id)));
  }

  function handleSave() {
    setSavedArticleIds(new Set(toggleSavedArticle(currentArticle.id)));
  }

  return <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
    <article className="mx-auto max-w-4xl">
      <Link to="/knowledge-hub" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-blue-600">
        <ArrowLeft size={18} />
        Back to Knowledge Base
      </Link>

      <header className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <p className="text-sm font-bold uppercase tracking-wide text-blue-600">{currentArticle.category}</p>
        <h1 className="mt-3 text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">{currentArticle.title}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          <span>{currentArticle.authorName}</span>
          <span>{currentArticle.sourceName}</span>
          <span>{formatDate(currentArticle.publishedAt)}</span>
        </div>
        <img src={currentArticle.coverImageUrl} alt={currentArticle.title} className="mx-auto mt-6 h-64 w-full max-w-2xl rounded-2xl object-cover sm:h-80" />
      </header>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <div className="mx-auto max-w-3xl space-y-5 text-base leading-8 text-slate-700">
          {currentArticle.contentBlocks.map((block, index) => <ArticleContentBlockView key={`${block.type}-${index}`} block={block} />)}
        </div>
        <div className="mx-auto mt-8 flex max-w-3xl flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <span className="inline-flex items-center gap-1.5"><Eye size={17} />Views {compactNumber(currentArticle.views)}</span>
            <button type="button" onClick={handleLike} className={actionClass(liked)} aria-pressed={liked}>
              <Heart size={17} fill={liked ? "currentColor" : "none"} />
              Likes {compactNumber(displayedLikes)}
            </button>
            <button type="button" onClick={handleSave} className={actionClass(saved)} aria-pressed={saved}>
              <Bookmark size={17} fill={saved ? "currentColor" : "none"} />
              Saves {compactNumber(displayedSaves)}
            </button>
          </div>
        </div>
      </section>
    </article>
  </main>;
}
