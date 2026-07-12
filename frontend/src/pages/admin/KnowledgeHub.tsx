import { ChangeEvent, FormEvent, useMemo, useRef, useState } from "react";
import {
  AlignCenter,
  AlignLeft,
  AlignRight,
  ArrowLeft,
  Bookmark,
  Bold,
  Eye,
  Heart,
  Image as ImageIcon,
  Italic,
  List,
  Pencil,
  Plus,
  Trash2,
  Underline,
  Upload,
  X,
} from "lucide-react";

type ArticleStatus = "Published" | "Draft";

type KnowledgeArticle = {
  id: number;
  title: string;
  excerpt: string;
  body: string;
  category: string;
  status: ArticleStatus;
  publishedAt: string | null;
  source: string;
  coverImage: string | null;
  inlineImages: string[];
  views: number;
  likes: number;
  saves: number;
};

type ArticleForm = {
  title: string;
  excerpt: string;
  body: string;
  category: string;
  source: string;
  status: ArticleStatus;
  coverImage: string | null;
  inlineImages: string[];
};

const categories = ["All", "Budgeting", "Saving", "Tax", "Superannuation", "Investing", "Security"];

const sampleArticles: KnowledgeArticle[] = [
  {
    id: 1,
    title: "How to Build a Budget That Survives Real Life",
    excerpt: "A simple guide to tracking income, planning spending and leaving room for irregular costs.",
    body: "A realistic budget starts with the money that actually arrives in your account and the spending that actually leaves it. Before setting a target, collect recent income, bills, subscriptions, groceries, transport costs and debt repayments.\n\nGroup your spending into needs, wants and savings. Needs are the costs required to keep daily life running. Wants are flexible lifestyle choices. Savings include emergency funds, short term goals and longer term wealth building.\n\nThe best budget is not the strictest one. It is the one you can review and actually keep using.",
    category: "Budgeting",
    status: "Published",
    publishedAt: "2026-07-02",
    source: "Knowledge Base Week",
    coverImage: null,
    inlineImages: [],
    views: 1800,
    likes: 127,
    saves: 88,
  },
  {
    id: 2,
    title: "Emergency Funds: Why Cash Still Matters",
    excerpt: "Before investing, keep enough cash aside for bills, repairs and unexpected income gaps.",
    body: "An emergency fund gives you time to respond when something expensive or stressful happens. It can reduce the chance of relying on credit cards or selling investments at the wrong time.",
    category: "Saving",
    status: "Published",
    publishedAt: "2026-06-26",
    source: "FinanceAI Learning Team",
    coverImage: null,
    inlineImages: [],
    views: 1360,
    likes: 98,
    saves: 64,
  },
  {
    id: 3,
    title: "Tax Time Checklist for First-Time Investors",
    excerpt: "A draft checklist for keeping records, statements and dividend information organised.",
    body: "Keep records of purchases, sales, dividends, interest and fees. This draft should be reviewed before publication.",
    category: "Tax",
    status: "Draft",
    publishedAt: null,
    source: "FinanceAI Learning Team",
    coverImage: null,
    inlineImages: [],
    views: 0,
    likes: 0,
    saves: 0,
  },
  {
    id: 4,
    title: "Superannuation Basics in Plain English",
    excerpt: "What super is, why it matters, and the first settings most people should check.",
    body: "Superannuation is a long-term retirement savings system. Small decisions around fund choice, insurance and contributions can compound over time.",
    category: "Superannuation",
    status: "Published",
    publishedAt: "2026-06-18",
    source: "Knowledge Base Week",
    coverImage: null,
    inlineImages: [],
    views: 920,
    likes: 73,
    saves: 41,
  },
  {
    id: 5,
    title: "Avoiding Common Online Finance Scams",
    excerpt: "Warning signs to look for before clicking links or sharing account details.",
    body: "Scammers often use urgency, impersonation and unusual payment requests. Pause, verify the source and never share codes or passwords.",
    category: "Security",
    status: "Published",
    publishedAt: "2026-06-12",
    source: "FinanceAI Learning Team",
    coverImage: null,
    inlineImages: [],
    views: 2140,
    likes: 166,
    saves: 102,
  },
  {
    id: 6,
    title: "Investing Terms New Users Ask About",
    excerpt: "A glossary draft covering ETFs, diversification, volatility and risk tolerance.",
    body: "This article draft will explain key investment terms in simple language.",
    category: "Investing",
    status: "Draft",
    publishedAt: null,
    source: "FinanceAI Learning Team",
    coverImage: null,
    inlineImages: [],
    views: 0,
    likes: 0,
    saves: 0,
  },
  {
    id: 7,
    title: "Saving for Short-Term Goals",
    excerpt: "How to separate travel, study and home deposit goals without mixing up your everyday money.",
    body: "Short-term savings work best when each goal is named, measured and reviewed regularly.",
    category: "Saving",
    status: "Published",
    publishedAt: "2026-06-05",
    source: "FinanceAI Learning Team",
    coverImage: null,
    inlineImages: [],
    views: 740,
    likes: 52,
    saves: 37,
  },
];

const emptyForm = (): ArticleForm => ({
  title: "",
  excerpt: "",
  body: "",
  category: "Budgeting",
  source: "FinanceAI Learning Team",
  status: "Draft",
  coverImage: null,
  inlineImages: [],
});

function formatPublishedDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

function shortText(value: string, max = 70) {
  return value.length > max ? `${value.slice(0, max).trim()}...` : value;
}

function categoryTone(category: string) {
  const tones: Record<string, string> = {
    Budgeting: "bg-violet-100 text-violet-700",
    Saving: "bg-blue-100 text-blue-700",
    Tax: "bg-amber-100 text-amber-700",
    Superannuation: "bg-emerald-100 text-emerald-700",
    Investing: "bg-indigo-100 text-indigo-700",
    Security: "bg-rose-100 text-rose-700",
  };
  return tones[category] ?? "bg-slate-100 text-slate-600";
}

function readImageFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Unable to read the selected image."));
    reader.readAsDataURL(file);
  });
}

function createFormFromArticle(article: KnowledgeArticle): ArticleForm {
  return {
    title: article.title,
    excerpt: article.excerpt,
    body: article.body,
    category: article.category,
    source: article.source,
    status: article.status,
    coverImage: article.coverImage,
    inlineImages: [...article.inlineImages],
  };
}

function ImageDropzone({
  image,
  onUpload,
  onRemove,
}: {
  image: string | null;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onRemove: () => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-950">Cover Image</h2>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="mt-4 grid min-h-44 w-full place-items-center overflow-hidden rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/60 text-center transition hover:border-violet-300 hover:bg-violet-50/40"
      >
        {image ? (
          <img src={image} alt="Cover preview" className="h-44 w-full object-cover" />
        ) : (
          <span className="flex flex-col items-center gap-3 px-4 text-slate-400">
            <Upload size={30} aria-hidden="true" />
            <span className="font-medium text-slate-500">Click to upload cover image</span>
            <span className="text-xs uppercase tracking-wide">PNG, JPG, WEBP</span>
          </span>
        )}
      </button>
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onUpload} />
      {image && (
        <button type="button" onClick={onRemove} className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-red-500 hover:text-red-700">
          <X size={16} /> Remove cover
        </button>
      )}
    </div>
  );
}

function EditorToolbar({ onImageUpload }: { onImageUpload: (event: ChangeEvent<HTMLInputElement>) => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 p-3 text-slate-600">
      <button type="button" className="grid size-9 place-items-center rounded-lg bg-violet-100 text-violet-700" aria-label="Paragraph"><List size={18} /></button>
      <button type="button" className="rounded-lg px-3 py-2 text-sm font-semibold hover:bg-white">H1</button>
      <button type="button" className="rounded-lg px-3 py-2 text-sm font-semibold hover:bg-white">H2</button>
      <span className="h-7 w-px bg-slate-200" />
      <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none">
        <option>Size</option>
        <option>Small</option>
        <option>Normal</option>
        <option>Large</option>
      </select>
      <span className="h-7 w-px bg-slate-200" />
      <button type="button" className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Bold"><Bold size={18} /></button>
      <button type="button" className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Italic"><Italic size={18} /></button>
      <button type="button" className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Underline"><Underline size={18} /></button>
      <span className="h-7 w-px bg-slate-200" />
      <button type="button" className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Align left"><AlignLeft size={18} /></button>
      <button type="button" className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Align center"><AlignCenter size={18} /></button>
      <button type="button" className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Align right"><AlignRight size={18} /></button>
      <span className="h-7 w-px bg-slate-200" />
      <select className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none">
        <option>Spacing</option>
        <option>Compact</option>
        <option>Relaxed</option>
      </select>
      <button type="button" onClick={() => inputRef.current?.click()} className="grid size-9 place-items-center rounded-lg hover:bg-white" aria-label="Insert image">
        <ImageIcon size={18} />
      </button>
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onImageUpload} />
    </div>
  );
}

function ArticleEditor({
  mode,
  form,
  setForm,
  metrics,
  onBack,
  onSave,
}: {
  mode: "new" | "edit";
  form: ArticleForm;
  setForm: (form: ArticleForm) => void;
  metrics?: Pick<KnowledgeArticle, "views" | "likes" | "saves">;
  onBack: () => void;
  onSave: (status: ArticleStatus) => void;
}) {
  const [imageError, setImageError] = useState("");

  async function handleCoverUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setImageError("");
      setForm({ ...form, coverImage: await readImageFile(file) });
    } catch (caught) {
      setImageError(caught instanceof Error ? caught.message : "Unable to upload image.");
    } finally {
      event.target.value = "";
    }
  }

  async function handleInlineUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setImageError("");
      const image = await readImageFile(file);
      setForm({ ...form, inlineImages: [...form.inlineImages, image] });
    } catch (caught) {
      setImageError(caught instanceof Error ? caught.message : "Unable to upload image.");
    } finally {
      event.target.value = "";
    }
  }

  function submit(status: ArticleStatus) {
    if (!form.title.trim()) {
      setImageError("Please enter an article title before saving.");
      return;
    }
    onSave(status);
  }

  return (
    <section className="min-h-screen bg-slate-50 p-5 sm:p-8 lg:p-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button type="button" onClick={onBack} className="inline-flex items-center gap-3 text-sm font-semibold text-slate-600 hover:text-slate-950">
          <ArrowLeft size={19} /> Back to Knowledge Hub
        </button>
        <div className="flex flex-wrap items-center gap-3">
          {mode === "new" && (
            <select
              value={form.status}
              onChange={(event) => setForm({ ...form, status: event.target.value as ArticleStatus })}
              className="rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-medium text-slate-800 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
            >
              <option value="Draft">Save as Draft</option>
              <option value="Published">Publish Now</option>
            </select>
          )}
          <button type="button" onClick={() => submit(mode === "new" ? form.status : "Published")} className="rounded-xl bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800">
            {mode === "new" ? (form.status === "Published" ? "Publish Article" : "Save Draft") : "Save Changes"}
          </button>
        </div>
      </header>

      {imageError && <p role="alert" className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{imageError}</p>}

      <form onSubmit={(event: FormEvent) => { event.preventDefault(); submit(mode === "new" ? form.status : "Published"); }} className="mt-8 grid gap-7 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-7">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <label htmlFor="article-title" className="text-lg font-semibold text-slate-950">Title</label>
            <input
              id="article-title"
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="Article title..."
              className="mt-3 w-full rounded-xl border-0 bg-slate-100 px-5 py-4 text-lg text-slate-950 outline-none transition placeholder:text-slate-400 focus:ring-4 focus:ring-violet-100"
            />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <label htmlFor="article-excerpt" className="text-lg font-semibold text-slate-950">Excerpt</label>
            <p className="mt-1 text-sm text-slate-500">Shown on the article card in the Knowledge Hub listing.</p>
            <textarea
              id="article-excerpt"
              value={form.excerpt}
              onChange={(event) => setForm({ ...form, excerpt: event.target.value })}
              placeholder="A short summary of the article..."
              rows={4}
              className="mt-4 w-full resize-none rounded-xl border border-slate-200 px-5 py-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
            />
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="p-6 pb-4">
              <label htmlFor="article-body" className="text-lg font-semibold text-slate-950">Article Body</label>
              <p className="mt-1 text-sm text-slate-500">Use the toolbar to format text and insert images inline.</p>
            </div>
            <EditorToolbar onImageUpload={handleInlineUpload} />
            <textarea
              id="article-body"
              value={form.body}
              onChange={(event) => setForm({ ...form, body: event.target.value })}
              placeholder="Start writing your article..."
              rows={12}
              className="w-full resize-y border-0 px-7 py-6 text-lg leading-8 text-slate-950 outline-none placeholder:text-slate-400"
            />
            {form.inlineImages.length > 0 && (
              <div className="grid gap-4 border-t border-slate-100 p-6 sm:grid-cols-2">
                {form.inlineImages.map((image, index) => (
                  <div key={`${image.slice(0, 40)}-${index}`} className="relative overflow-hidden rounded-xl border border-slate-200">
                    <img src={image} alt={`Inline article upload ${index + 1}`} className="h-44 w-full object-cover" />
                    <button
                      type="button"
                      onClick={() => setForm({ ...form, inlineImages: form.inlineImages.filter((_, imageIndex) => imageIndex !== index) })}
                      className="absolute right-2 top-2 grid size-8 place-items-center rounded-full bg-white/90 text-slate-600 shadow-sm hover:text-red-600"
                      aria-label="Remove inline image"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-6">
          <ImageDropzone image={form.coverImage} onUpload={handleCoverUpload} onRemove={() => setForm({ ...form, coverImage: null })} />
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-950">Article Details</h2>
            <label htmlFor="article-category" className="mt-6 block text-sm font-semibold text-slate-500">Category</label>
            <select
              id="article-category"
              value={form.category}
              onChange={(event) => setForm({ ...form, category: event.target.value })}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
            >
              {categories.filter((category) => category !== "All").map((category) => <option key={category}>{category}</option>)}
            </select>
            <label htmlFor="article-source" className="mt-6 block text-sm font-semibold text-slate-500">Source / Author</label>
            <input
              id="article-source"
              value={form.source}
              onChange={(event) => setForm({ ...form, source: event.target.value })}
              className="mt-2 w-full rounded-xl border-0 bg-slate-100 px-4 py-3 text-slate-950 outline-none focus:ring-4 focus:ring-violet-100"
            />
            <span className={`mt-6 inline-flex rounded-full px-3 py-1 text-sm font-medium ${categoryTone(form.category)}`}>{form.category}</span>
          </div>
          {metrics && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-950">Engagement Stats</h2>
              <div className="mt-5 space-y-4 text-sm text-slate-500">
                <div className="flex items-center justify-between"><span className="inline-flex items-center gap-3"><Eye size={18} /> Views</span><strong className="text-slate-900">{metrics.views.toLocaleString()}</strong></div>
                <div className="flex items-center justify-between"><span className="inline-flex items-center gap-3"><Heart size={18} className="text-red-500" /> Likes</span><strong className="text-slate-900">{metrics.likes.toLocaleString()}</strong></div>
                <div className="flex items-center justify-between"><span className="inline-flex items-center gap-3"><Bookmark size={18} className="text-indigo-500" /> Saves</span><strong className="text-slate-900">{metrics.saves.toLocaleString()}</strong></div>
              </div>
            </div>
          )}
        </aside>
      </form>
    </section>
  );
}

export default function AdminKnowledgeHub() {
  const [articles, setArticles] = useState<KnowledgeArticle[]>(sampleArticles);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [editorMode, setEditorMode] = useState<"list" | "new" | "edit">("list");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ArticleForm>(emptyForm);

  const counts = useMemo(() => ({
    published: articles.filter((article) => article.status === "Published").length,
    drafts: articles.filter((article) => article.status === "Draft").length,
  }), [articles]);

  const visibleArticles = useMemo(() => (
    selectedCategory === "All" ? articles : articles.filter((article) => article.category === selectedCategory)
  ), [articles, selectedCategory]);

  const editingArticle = editingId ? articles.find((article) => article.id === editingId) ?? null : null;

  function openNewArticle() {
    setForm(emptyForm());
    setEditingId(null);
    setEditorMode("new");
  }

  function openEditArticle(article: KnowledgeArticle) {
    setForm(createFormFromArticle(article));
    setEditingId(article.id);
    setEditorMode("edit");
  }

  function saveNewArticle(status: ArticleStatus) {
    const nextArticle: KnowledgeArticle = {
      id: Math.max(...articles.map((article) => article.id), 0) + 1,
      title: form.title.trim(),
      excerpt: form.excerpt.trim(),
      body: form.body.trim(),
      category: form.category,
      status,
      publishedAt: status === "Published" ? new Date().toISOString().slice(0, 10) : null,
      source: form.source.trim() || "FinanceAI Learning Team",
      coverImage: form.coverImage,
      inlineImages: [...form.inlineImages],
      views: 0,
      likes: 0,
      saves: 0,
    };
    setArticles((current) => [nextArticle, ...current]);
    setEditorMode("list");
  }

  function saveEditedArticle(status: ArticleStatus) {
    if (!editingArticle) return;
    setArticles((current) => current.map((article) => article.id === editingArticle.id ? {
      ...article,
      title: form.title.trim(),
      excerpt: form.excerpt.trim(),
      body: form.body.trim(),
      category: form.category,
      status,
      publishedAt: status === "Published" ? article.publishedAt ?? new Date().toISOString().slice(0, 10) : null,
      source: form.source.trim() || "FinanceAI Learning Team",
      coverImage: form.coverImage,
      inlineImages: [...form.inlineImages],
    } : article));
    setEditorMode("list");
    setEditingId(null);
  }

  function deleteArticle(articleId: number) {
    const article = articles.find((item) => item.id === articleId);
    if (!article || !window.confirm(`Delete "${article.title}"? This action cannot be undone.`)) return;
    setArticles((current) => current.filter((item) => item.id !== articleId));
  }

  if (editorMode === "new") {
    return <ArticleEditor mode="new" form={form} setForm={setForm} onBack={() => setEditorMode("list")} onSave={saveNewArticle} />;
  }

  if (editorMode === "edit" && editingArticle) {
    return <ArticleEditor mode="edit" form={form} setForm={setForm} metrics={editingArticle} onBack={() => setEditorMode("list")} onSave={saveEditedArticle} />;
  }

  return (
    <section className="p-5 sm:p-8 lg:p-12">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Knowledge Hub</h1>
          <div className="mt-3 flex flex-wrap gap-3 text-sm font-medium">
            <span className="rounded-full bg-emerald-50 px-4 py-1.5 text-emerald-700">{counts.published} published</span>
            <span className="rounded-full bg-amber-50 px-4 py-1.5 text-amber-700">{counts.drafts} drafts</span>
          </div>
        </div>
        <button type="button" onClick={openNewArticle} className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-6 py-3.5 font-semibold text-white transition hover:bg-slate-800">
          <Plus size={20} /> New Article
        </button>
      </header>

      <div className="mt-8 flex flex-wrap gap-3">
        {categories.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setSelectedCategory(category)}
            className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${selectedCategory === category ? "bg-indigo-500 text-white shadow-sm" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1040px] text-left">
            <thead className="border-b border-slate-200 bg-slate-50/70 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-6 py-5">Article</th>
                <th className="px-6 py-5">Category</th>
                <th className="px-6 py-5">Status</th>
                <th className="px-6 py-5">Published</th>
                <th className="px-6 py-5">Views</th>
                <th className="px-6 py-5">Likes</th>
                <th className="px-6 py-5">Saves</th>
                <th className="px-6 py-5">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {visibleArticles.map((article) => (
                <tr key={article.id} className="align-middle transition hover:bg-slate-50/70">
                  <td className="px-6 py-6">
                    <div className="flex max-w-md gap-4">
                      <div className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-xl border border-slate-200 bg-slate-100 text-slate-300">
                        {article.coverImage ? <img src={article.coverImage} alt="" className="h-full w-full object-cover" /> : <ImageIcon size={24} />}
                      </div>
                      <div>
                        <h2 className="font-bold leading-snug text-slate-900">{article.title}</h2>
                        <p className="mt-2 text-sm leading-5 text-slate-500">{shortText(article.excerpt, 58)}</p>
                        <p className="mt-2 text-xs font-semibold text-slate-300">{article.source}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-6"><span className={`rounded-full px-3 py-1 text-sm font-medium ${categoryTone(article.category)}`}>{article.category}</span></td>
                  <td className="px-6 py-6"><span className={`rounded-full px-3 py-1 text-sm font-semibold ${article.status === "Published" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{article.status}</span></td>
                  <td className="px-6 py-6 text-sm text-slate-500">{formatPublishedDate(article.publishedAt)}</td>
                  <td className="px-6 py-6 text-sm text-slate-600"><span className="inline-flex items-center gap-2"><Eye size={16} className="text-slate-400" />{article.views.toLocaleString()}</span></td>
                  <td className="px-6 py-6 text-sm text-slate-600"><span className="inline-flex items-center gap-2"><Heart size={16} className="text-red-500" />{article.likes.toLocaleString()}</span></td>
                  <td className="px-6 py-6 text-sm text-slate-600"><span className="inline-flex items-center gap-2"><Bookmark size={16} className="text-indigo-500" />{article.saves.toLocaleString()}</span></td>
                  <td className="px-6 py-6">
                    <div className="flex items-center gap-4 whitespace-nowrap">
                      <button type="button" onClick={() => openEditArticle(article)} className="inline-flex items-center gap-1.5 font-semibold text-indigo-600 hover:text-indigo-800">
                        <Pencil size={17} /> Edit
                      </button>
                      <button type="button" onClick={() => deleteArticle(article.id)} className="inline-flex items-center gap-1.5 font-semibold text-red-500 hover:text-red-700">
                        <Trash2 size={17} /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {visibleArticles.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-16 text-center text-slate-500">No articles in this category yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
