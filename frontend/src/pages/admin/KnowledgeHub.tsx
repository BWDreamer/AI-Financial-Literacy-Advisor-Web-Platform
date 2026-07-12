import { ChangeEvent, Dispatch, FormEvent, SetStateAction, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "@tiptap/extension-image";
import TextAlign from "@tiptap/extension-text-align";
import UnderlineExtension from "@tiptap/extension-underline";
import { Editor, EditorContent, JSONContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
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
  RefreshCw,
  Trash2,
  Underline,
  Upload,
  X,
} from "lucide-react";
import { API_ORIGIN } from "../../api/client";
import {
  AdminArticleContentBlock,
  createAdminArticle,
  deleteAdminArticle,
  getPublishedAdminArticle,
  getPublishedAdminArticles,
  updateAdminArticle,
  uploadAdminArticleImage,
} from "../../api/admin";
import type { Article, ArticleDetail } from "../../api/articles";

type ArticleForm = {
  title: string;
  summary: string;
  contentBlocks: AdminArticleContentBlock[];
  category: string;
  authorName: string;
  sourceName: string;
  coverImageUrl: string | null;
};

const categories = ["All", "Budgeting", "Saving", "Tax", "Superannuation", "Investing", "Security"];

const emptyForm = (): ArticleForm => ({
  title: "",
  summary: "",
  contentBlocks: [],
  category: "Budgeting",
  authorName: "FinanceAI Learning Team",
  sourceName: "Knowledge Base",
  coverImageUrl: null,
});

function errorMessage(caught: unknown) {
  return caught instanceof Error ? caught.message : "Something went wrong. Please try again.";
}

function imageSrc(value: string | null) {
  if (!value) return null;
  if (/^https?:\/\//i.test(value) || value.startsWith("data:")) return value;
  return `${API_ORIGIN}${value}`;
}

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

function slugify(value: string) {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 70);
  return `${slug || "article"}-${Date.now().toString(36)}`;
}

function contentBlocksToText(blocks: AdminArticleContentBlock[]) {
  return blocks
    .filter((block): block is Extract<AdminArticleContentBlock, { type: "paragraph" }> => block.type === "paragraph")
    .map((block) => block.text.trim())
    .filter(Boolean)
    .join("\n\n");
}

function blocksToTipTapContent(blocks: AdminArticleContentBlock[]): JSONContent {
  const content = blocks.flatMap((block): JSONContent[] => {
    if (block.type === "image") {
      return [{
        type: "image",
        attrs: {
          src: imageSrc(block.src) ?? block.src,
          alt: block.alt,
          title: block.caption ?? null,
        },
      }];
    }

    return block.text.split("\n").map((line) => ({
      type: "paragraph",
      content: line ? [{ type: "text", text: line }] : [],
    }));
  });

  return {
    type: "doc",
    content: content.length ? content : [{ type: "paragraph" }],
  };
}

function extractText(node: JSONContent): string {
  if (node.type === "text") return node.text ?? "";
  return node.content?.map(extractText).join("") ?? "";
}

function normalizeStoredImageUrl(src: string) {
  if (src.startsWith(API_ORIGIN)) return src.slice(API_ORIGIN.length);
  return src;
}

function tipTapContentToBlocks(doc: JSONContent): AdminArticleContentBlock[] {
  const blocks: AdminArticleContentBlock[] = [];

  function visit(node: JSONContent) {
    if (node.type === "image" && typeof node.attrs?.src === "string") {
      blocks.push({
        type: "image",
        src: normalizeStoredImageUrl(node.attrs.src),
        alt: typeof node.attrs.alt === "string" && node.attrs.alt ? node.attrs.alt : `Article image ${blocks.filter((block) => block.type === "image").length + 1}`,
        ...(typeof node.attrs.title === "string" && node.attrs.title ? { caption: node.attrs.title } : {}),
      });
      return;
    }

    if (node.type === "paragraph" || node.type === "heading") {
      const text = extractText(node).trim();
      if (text) blocks.push({ type: "paragraph", text });
      return;
    }

    node.content?.forEach(visit);
  }

  doc.content?.forEach(visit);
  return blocks;
}

function articleDetailToForm(article: ArticleDetail): ArticleForm {
  return {
    title: article.title,
    summary: article.summary,
    contentBlocks: article.contentBlocks,
    category: article.category,
    authorName: article.authorName,
    sourceName: article.sourceName,
    coverImageUrl: article.coverImageUrl,
  };
}

function ImageDropzone({
  image,
  onUpload,
  onRemove,
  disabled,
}: {
  image: string | null;
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void;
  onRemove: () => void;
  disabled: boolean;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-950">Cover Image</h2>
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="mt-4 grid min-h-44 w-full place-items-center overflow-hidden rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/60 text-center transition hover:border-violet-300 hover:bg-violet-50/40 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {image ? (
          <img src={imageSrc(image) ?? undefined} alt="Cover preview" className="h-44 w-full object-cover" />
        ) : (
          <span className="flex flex-col items-center gap-3 px-4 text-slate-400">
            <Upload size={30} aria-hidden="true" />
            <span className="font-medium text-slate-500">Click to upload cover image</span>
            <span className="text-xs uppercase tracking-wide">PNG, JPG, WEBP</span>
          </span>
        )}
      </button>
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onUpload} disabled={disabled} />
      {image && (
        <button type="button" disabled={disabled} onClick={onRemove} className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-red-500 hover:text-red-700 disabled:opacity-60">
          <X size={16} /> Remove cover
        </button>
      )}
    </div>
  );
}

function toolbarButtonClass(active = false) {
  return [
    "grid size-9 place-items-center rounded-lg transition",
    active ? "bg-violet-100 text-violet-700" : "hover:bg-white",
  ].join(" ");
}

function EditorToolbar({ editor, onImageUpload, disabled }: { editor: Editor | null; onImageUpload: (event: ChangeEvent<HTMLInputElement>) => void; disabled: boolean }) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 p-3 text-slate-600">
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().setParagraph().run()} className={toolbarButtonClass(editor?.isActive("paragraph"))} aria-label="Paragraph"><List size={18} /></button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()} className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${editor?.isActive("heading", { level: 1 }) ? "bg-violet-100 text-violet-700" : "hover:bg-white"}`}>H1</button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${editor?.isActive("heading", { level: 2 }) ? "bg-violet-100 text-violet-700" : "hover:bg-white"}`}>H2</button>
      <span className="h-7 w-px bg-slate-200" />
      <select disabled className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none disabled:opacity-60">
        <option>Size</option>
        <option>Small</option>
        <option>Normal</option>
        <option>Large</option>
      </select>
      <span className="h-7 w-px bg-slate-200" />
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleBold().run()} className={toolbarButtonClass(editor?.isActive("bold"))} aria-label="Bold"><Bold size={18} /></button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleItalic().run()} className={toolbarButtonClass(editor?.isActive("italic"))} aria-label="Italic"><Italic size={18} /></button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleUnderline().run()} className={toolbarButtonClass(editor?.isActive("underline"))} aria-label="Underline"><Underline size={18} /></button>
      <span className="h-7 w-px bg-slate-200" />
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().setTextAlign("left").run()} className={toolbarButtonClass(editor?.isActive({ textAlign: "left" }))} aria-label="Align left"><AlignLeft size={18} /></button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().setTextAlign("center").run()} className={toolbarButtonClass(editor?.isActive({ textAlign: "center" }))} aria-label="Align center"><AlignCenter size={18} /></button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().setTextAlign("right").run()} className={toolbarButtonClass(editor?.isActive({ textAlign: "right" }))} aria-label="Align right"><AlignRight size={18} /></button>
      <span className="h-7 w-px bg-slate-200" />
      <select disabled className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none disabled:opacity-60">
        <option>Spacing</option>
        <option>Compact</option>
        <option>Relaxed</option>
      </select>
      <button type="button" disabled={disabled} onClick={() => inputRef.current?.click()} className="grid size-9 place-items-center rounded-lg hover:bg-white disabled:opacity-50" aria-label="Insert image">
        <ImageIcon size={18} />
      </button>
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onImageUpload} disabled={disabled} />
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
  saving,
}: {
  mode: "new" | "edit";
  form: ArticleForm;
  setForm: Dispatch<SetStateAction<ArticleForm>>;
  metrics?: Pick<Article, "views" | "likes" | "saves">;
  onBack: () => void;
  onSave: (contentBlocks: AdminArticleContentBlock[]) => Promise<void>;
  saving: boolean;
}) {
  const [formError, setFormError] = useState("");
  const [uploading, setUploading] = useState(false);
  const disabled = saving || uploading;
  const editor = useEditor({
    extensions: [
      StarterKit,
      UnderlineExtension,
      Image.configure({ inline: false, allowBase64: false }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
    ],
    content: blocksToTipTapContent(form.contentBlocks),
    editorProps: {
      attributes: {
        class: "min-h-80 px-7 py-6 text-lg leading-8 text-slate-950 outline-none prose prose-slate max-w-none [&_img]:mx-auto [&_img]:my-6 [&_img]:max-h-80 [&_img]:rounded-2xl [&_img]:object-cover",
      },
    },
    onUpdate: ({ editor: updatedEditor }) => {
      setForm((current) => ({
        ...current,
        contentBlocks: tipTapContentToBlocks(updatedEditor.getJSON()),
      }));
    },
  });

  async function handleCoverUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      setFormError("");
      const { imageUrl } = await uploadAdminArticleImage(file);
      setForm({ ...form, coverImageUrl: imageUrl });
    } catch (caught) {
      setFormError(errorMessage(caught));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleInlineUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setUploading(true);
      setFormError("");
      const { imageUrl } = await uploadAdminArticleImage(file);
      editor?.chain().focus().setImage({ src: imageSrc(imageUrl) ?? imageUrl, alt: "Article image" }).run();
    } catch (caught) {
      setFormError(errorMessage(caught));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function submit() {
    const currentBlocks = editor ? tipTapContentToBlocks(editor.getJSON()) : form.contentBlocks;
    if (!form.title.trim() || !form.summary.trim() || !contentBlocksToText(currentBlocks).trim()) {
      setFormError("Please complete the title, excerpt and article body before saving.");
      return;
    }
    setForm((current) => ({ ...current, contentBlocks: currentBlocks }));
    setFormError("");
    await onSave(currentBlocks);
  }

  return (
    <section className="min-h-screen bg-slate-50 p-5 sm:p-8 lg:p-10">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <button type="button" onClick={onBack} disabled={disabled} className="inline-flex items-center gap-3 text-sm font-semibold text-slate-600 hover:text-slate-950 disabled:opacity-60">
          <ArrowLeft size={19} /> Back to Knowledge Hub
        </button>
        <button type="button" onClick={() => void submit()} disabled={disabled} className="rounded-xl bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
          {saving ? "Saving..." : mode === "new" ? "Publish Article" : "Save Changes"}
        </button>
      </header>

      {formError && <p role="alert" className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{formError}</p>}
      {uploading && <p className="mt-6 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-700">Uploading image...</p>}

      <form onSubmit={(event: FormEvent) => { event.preventDefault(); void submit(); }} className="mt-8 grid gap-7 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-7">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <label htmlFor="article-title" className="text-lg font-semibold text-slate-950">Title</label>
            <input id="article-title" value={form.title} disabled={disabled} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Article title..." className="mt-3 w-full rounded-xl border-0 bg-slate-100 px-5 py-4 text-lg text-slate-950 outline-none transition placeholder:text-slate-400 focus:ring-4 focus:ring-violet-100 disabled:opacity-70" />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <label htmlFor="article-summary" className="text-lg font-semibold text-slate-950">Excerpt</label>
            <textarea id="article-summary" value={form.summary} disabled={disabled} onChange={(event) => setForm({ ...form, summary: event.target.value })} placeholder="A short summary of the article..." rows={4} className="mt-4 w-full resize-none rounded-xl border border-slate-200 px-5 py-4 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-violet-500 focus:ring-4 focus:ring-violet-100 disabled:opacity-70" />
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="p-6 pb-4">
              <label htmlFor="article-body" className="text-lg font-semibold text-slate-950">Article Body</label>
            </div>
            <EditorToolbar editor={editor} onImageUpload={handleInlineUpload} disabled={disabled} />
            <EditorContent id="article-body" editor={editor} className="border-0 bg-white" />
          </div>
        </div>

        <aside className="space-y-6">
          <ImageDropzone image={form.coverImageUrl} onUpload={handleCoverUpload} onRemove={() => setForm({ ...form, coverImageUrl: null })} disabled={disabled} />
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold text-slate-950">Article Details</h2>
            <label htmlFor="article-category" className="mt-6 block text-sm font-semibold text-slate-500">Category</label>
            <select id="article-category" value={form.category} disabled={disabled} onChange={(event) => setForm({ ...form, category: event.target.value })} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100 disabled:opacity-70">
              {categories.filter((category) => category !== "All").map((category) => <option key={category}>{category}</option>)}
            </select>
            <label htmlFor="article-author" className="mt-6 block text-sm font-semibold text-slate-500">Author</label>
            <input id="article-author" value={form.authorName} disabled={disabled} onChange={(event) => setForm({ ...form, authorName: event.target.value })} className="mt-2 w-full rounded-xl border-0 bg-slate-100 px-4 py-3 text-slate-950 outline-none focus:ring-4 focus:ring-violet-100 disabled:opacity-70" />
            <label htmlFor="article-source" className="mt-6 block text-sm font-semibold text-slate-500">Source</label>
            <input id="article-source" value={form.sourceName} disabled={disabled} onChange={(event) => setForm({ ...form, sourceName: event.target.value })} className="mt-2 w-full rounded-xl border-0 bg-slate-100 px-4 py-3 text-slate-950 outline-none focus:ring-4 focus:ring-violet-100 disabled:opacity-70" />
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
  const [articles, setArticles] = useState<Article[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [editorMode, setEditorMode] = useState<"list" | "new" | "edit">("list");
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [form, setForm] = useState<ArticleForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [saving, setSaving] = useState(false);

  const loadArticles = useCallback(async () => {
    setLoading(true);
    try {
      const page = await getPublishedAdminArticles();
      setArticles(page.items);
      setPageError("");
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadArticles();
  }, [loadArticles]);

  const visibleArticles = useMemo(() => (
    selectedCategory === "All" ? articles : articles.filter((article) => article.category === selectedCategory)
  ), [articles, selectedCategory]);

  function openNewArticle() {
    setForm(emptyForm());
    setEditingArticle(null);
    setEditorMode("new");
  }

  async function openEditArticle(article: Article) {
    setSaving(true);
    setPageError("");
    try {
      const detail = await getPublishedAdminArticle(article.id);
      setForm(articleDetailToForm(detail));
      setEditingArticle(detail);
      setEditorMode("edit");
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  function requestFromForm(id?: string, contentBlocks = form.contentBlocks) {
    return {
      ...(id ? { id } : {}),
      title: form.title.trim(),
      summary: form.summary.trim(),
      coverImageUrl: form.coverImageUrl,
      authorName: form.authorName.trim() || "FinanceAI Learning Team",
      sourceName: form.sourceName.trim() || "Knowledge Base",
      category: form.category,
      status: "published" as const,
      publishedAt: new Date().toISOString(),
      contentBlocks,
    };
  }

  async function saveNewArticle(contentBlocks: AdminArticleContentBlock[]) {
    setSaving(true);
    try {
      const request = {
        ...requestFromForm(undefined, contentBlocks),
        id: slugify(form.title),
      };
      await createAdminArticle(request);
      await loadArticles();
      setEditorMode("list");
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  async function saveEditedArticle(contentBlocks: AdminArticleContentBlock[]) {
    if (!editingArticle) return;
    setSaving(true);
    try {
      await updateAdminArticle(editingArticle.id, requestFromForm(undefined, contentBlocks));
      await loadArticles();
      setEditorMode("list");
      setEditingArticle(null);
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  async function removeArticle(article: Article) {
    if (!window.confirm(`Delete "${article.title}"? This action cannot be undone.`)) return;
    setSaving(true);
    try {
      await deleteAdminArticle(article.id);
      setArticles((current) => current.filter((item) => item.id !== article.id));
      setPageError("");
    } catch (caught) {
      setPageError(errorMessage(caught));
    } finally {
      setSaving(false);
    }
  }

  if (editorMode === "new") {
    return <ArticleEditor mode="new" form={form} setForm={setForm} onBack={() => setEditorMode("list")} onSave={saveNewArticle} saving={saving} />;
  }

  if (editorMode === "edit" && editingArticle) {
    return <ArticleEditor mode="edit" form={form} setForm={setForm} metrics={editingArticle} onBack={() => setEditorMode("list")} onSave={saveEditedArticle} saving={saving} />;
  }

  return (
    <section className="p-5 sm:p-8 lg:p-12">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">Knowledge Hub</h1>
          <div className="mt-3 flex flex-wrap gap-3 text-sm font-medium">
            <span className="rounded-full bg-emerald-50 px-4 py-1.5 text-emerald-700">{articles.length} published</span>
          </div>
        </div>
        <button type="button" onClick={openNewArticle} disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-6 py-3.5 font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
          <Plus size={20} /> New Article
        </button>
      </header>

      {pageError && (
        <div role="alert" className="mt-6 flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:flex-row sm:items-center sm:justify-between">
          <span>{pageError}</span>
          <button type="button" onClick={() => void loadArticles()} className="inline-flex items-center gap-2 font-semibold"><RefreshCw size={16} /> Try Again</button>
        </div>
      )}

      <div className="mt-8 flex flex-wrap gap-3">
        {categories.map((category) => (
          <button key={category} type="button" onClick={() => setSelectedCategory(category)} className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${selectedCategory === category ? "bg-indigo-500 text-white shadow-sm" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
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
              {loading && <tr><td colSpan={8} className="px-6 py-16 text-center text-slate-500">Loading articles...</td></tr>}
              {!loading && visibleArticles.map((article) => (
                <tr key={article.id} className="align-middle transition hover:bg-slate-50/70">
                  <td className="px-6 py-6">
                    <div className="flex max-w-md gap-4">
                      <div className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-xl border border-slate-200 bg-slate-100 text-slate-300">
                        {article.coverImageUrl ? <img src={imageSrc(article.coverImageUrl) ?? undefined} alt="" className="h-full w-full object-cover" /> : <ImageIcon size={24} />}
                      </div>
                      <div>
                        <h2 className="font-bold leading-snug text-slate-900">{article.title}</h2>
                        <p className="mt-2 text-sm leading-5 text-slate-500">{shortText(article.summary, 58)}</p>
                        <p className="mt-2 text-xs font-semibold text-slate-300">{article.sourceName}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-6"><span className={`rounded-full px-3 py-1 text-sm font-medium ${categoryTone(article.category)}`}>{article.category}</span></td>
                  <td className="px-6 py-6"><span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">Published</span></td>
                  <td className="px-6 py-6 text-sm text-slate-500">{formatPublishedDate(article.publishedAt)}</td>
                  <td className="px-6 py-6 text-sm text-slate-600"><span className="inline-flex items-center gap-2"><Eye size={16} className="text-slate-400" />{article.views.toLocaleString()}</span></td>
                  <td className="px-6 py-6 text-sm text-slate-600"><span className="inline-flex items-center gap-2"><Heart size={16} className="text-red-500" />{article.likes.toLocaleString()}</span></td>
                  <td className="px-6 py-6 text-sm text-slate-600"><span className="inline-flex items-center gap-2"><Bookmark size={16} className="text-indigo-500" />{article.saves.toLocaleString()}</span></td>
                  <td className="px-6 py-6">
                    <div className="flex items-center gap-4 whitespace-nowrap">
                      <button type="button" disabled={saving} onClick={() => void openEditArticle(article)} className="inline-flex items-center gap-1.5 font-semibold text-indigo-600 hover:text-indigo-800 disabled:opacity-60">
                        <Pencil size={17} /> Edit
                      </button>
                      <button type="button" disabled={saving} onClick={() => void removeArticle(article)} className="inline-flex items-center gap-1.5 font-semibold text-red-500 hover:text-red-700 disabled:opacity-60">
                        <Trash2 size={17} /> Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && visibleArticles.length === 0 && !pageError && (
                <tr>
                  <td colSpan={8} className="px-6 py-16 text-center text-slate-500">No published articles in this category yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
