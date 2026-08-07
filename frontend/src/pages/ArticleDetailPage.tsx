import { ArrowLeft, Bookmark, Eye, Heart } from "lucide-react";
import { Link, Navigate, useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import {
  getArticle,
  incrementArticleViews,
  likeArticle,
  saveArticle,
  unlikeArticle,
  unsaveArticle,
  type ArticleDetail,
} from "../api/articles";
import { ApiError } from "../api/client";
import ArticleContentRenderer from "../components/knowledge/ArticleContentRenderer";
import { useUser } from "../store/UserProvider";
import { resolveImageUrl } from "../utils/imageUrl";

function formatDate(value: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-AU", { month: "long", day: "numeric", year: "numeric" });
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-AU", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function actionClass(active: boolean) {
  return [
    "inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-sm font-medium transition",
    active ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-50 hover:text-blue-600",
  ].join(" ");
}

export default function ArticleDetailPage() {
  const { articleId } = useParams();
  const { user } = useUser();
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const viewedArticleIdRef = useRef<string | null>(null);

  function shouldIncrementArticleViews() {
    return Boolean(articleId && user && user.role !== "admin");
  }

  useEffect(() => {
    if (!articleId) {
      setNotFound(true);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    getArticle(articleId)
      .then((data) => {
        if (active) setArticle(data);
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
        else setError(err instanceof Error ? err.message : "Unable to load this article.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [articleId]);

  useEffect(() => {
    if (!article || !shouldIncrementArticleViews()) return;
    if (viewedArticleIdRef.current === article.id) return;

    viewedArticleIdRef.current = article.id;
    incrementArticleViews(article.id)
      .then((result) => {
        setArticle((currentArticle) => currentArticle?.id === result.articleId
          ? { ...currentArticle, views: result.views }
          : currentArticle);
      })
      .catch(() => undefined);
  }, [article, articleId, user]);

  if (notFound) return <Navigate to="/knowledge-hub" replace />;
  if (loading) return <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8"><section className="mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">Loading article...</section></main>;
  if (error) return <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8"><section className="mx-auto max-w-4xl rounded-2xl border border-red-100 bg-red-50 p-8 text-center text-red-600">{error}</section></main>;
  if (!article) return null;
  const coverImageUrl = resolveImageUrl(article.coverImageUrl);

  async function handleLike() {
    if (!article) return;
    try {
      const result = article.likedByMe
        ? await unlikeArticle(article.id)
        : await likeArticle(article.id);
      setArticle({ ...article, likedByMe: result.liked, likes: result.likes });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please sign in to like articles.");
    }
  }

  async function handleSave() {
    if (!article) return;
    try {
      const result = article.savedByMe
        ? await unsaveArticle(article.id)
        : await saveArticle(article.id);
      setArticle({ ...article, savedByMe: result.saved, saves: result.saves });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please sign in to save articles.");
    }
  }

  return <main className="min-h-screen bg-slate-50 px-4 py-6 sm:px-6 lg:px-8">
    <article className="mx-auto max-w-4xl">
      <Link to="/knowledge-hub" className="inline-flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-blue-600">
        <ArrowLeft size={18} />
        Back to Knowledge Base
      </Link>

      <header className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <p className="text-sm font-bold uppercase tracking-wide text-blue-600">{article.category}</p>
        <h1 className="mt-3 text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">{article.title}</h1>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-500">
          <span>{article.authorName}</span>
          {article.sourceUrl ? (
            <a href={article.sourceUrl} target="_blank" rel="noreferrer" className="font-semibold text-blue-600 hover:underline">
              {article.sourceName}
            </a>
          ) : <span>{article.sourceName}</span>}
          <span>{formatDate(article.publishedAt)}</span>
        </div>
        {coverImageUrl && <img src={coverImageUrl} alt={article.title} className="mx-auto mt-6 h-64 w-full max-w-2xl rounded-2xl object-cover sm:h-80" />}
      </header>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <ArticleContentRenderer contentBlocks={article.contentBlocks} />
        <div className="mx-auto mt-8 flex max-w-3xl flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <span className="inline-flex items-center gap-1.5"><Eye size={17} />Views {compactNumber(article.views)}</span>
            <button type="button" onClick={handleLike} className={actionClass(article.likedByMe)} aria-pressed={article.likedByMe}>
              <Heart size={17} fill={article.likedByMe ? "currentColor" : "none"} />
              Likes {compactNumber(article.likes)}
            </button>
            <button type="button" onClick={handleSave} className={actionClass(article.savedByMe)} aria-pressed={article.savedByMe}>
              <Bookmark size={17} fill={article.savedByMe ? "currentColor" : "none"} />
              Saves {compactNumber(article.saves)}
            </button>
          </div>
        </div>
      </section>
    </article>
  </main>;
}
