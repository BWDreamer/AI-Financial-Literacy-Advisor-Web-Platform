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
  Search,
  Trash2,
  Underline,
  Upload,
  X,
} from "lucide-react";
import { API_ORIGIN } from "../../api/client";
import Modal from "../../components/Modal";
import { RichTextBlockStyle, fontSizeOptions, spacingOptions } from "../../components/knowledge/richTextExtensions";
import {
  AdminArticleContentBlocks,
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
  contentBlocks: AdminArticleContentBlocks;
  category: string;
  authorName: string;
  sourceName: string;
  coverImageUrl: string | null;
};

const categories = ["All", "Budgeting", "Saving", "Tax", "Superannuation", "Investing", "Security"];
const PAGE_SIZE = 10;

const sortOptions = [
  { value: "published-desc", label: "Newest published" },
  { value: "published-asc", label: "Oldest published" },
  { value: "views-desc", label: "Most views" },
  { value: "likes-desc", label: "Most likes" },
  { value: "saves-desc", label: "Most saves" },
] as const;

type SortOption = (typeof sortOptions)[number]["value"];

const emptyForm = (): ArticleForm => ({
  title: "",
  summary: "",
  contentBlocks: { type: "doc", content: [{ type: "paragraph" }] },
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

function useMobileListView() {
  const [mobile, setMobile] = useState(() => window.innerWidth < 1024);
  useEffect(() => {
    function resize() {
      setMobile(window.innerWidth < 1024);
    }
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, []);
  return mobile;
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

function contentBlocksToText(contentBlocks: AdminArticleContentBlocks) {
  return extractText(contentBlocksToTipTapDoc(contentBlocks)).trim();
}

function normalizeStoredImageNode(node: JSONContent): JSONContent {
  const attrs = node.attrs ? { ...node.attrs } : undefined;

  if (node.type === "image" && typeof attrs?.src === "string") {
    attrs.src = normalizeStoredImageUrl(attrs.src);
  }

  return {
    ...node,
    ...(attrs ? { attrs } : {}),
    ...(node.content ? { content: node.content.map(normalizeStoredImageNode) } : {}),
  };
}

function blockToTipTapNode(block: JSONContent): JSONContent {
  if (block.type === "image") {
    const src = typeof block.src === "string" ? block.src : block.attrs?.src;
    const alt = typeof block.alt === "string" ? block.alt : block.attrs?.alt;
    const caption = typeof block.caption === "string" ? block.caption : block.attrs?.title;

    return {
      type: "image",
      attrs: {
        src: typeof src === "string" ? imageSrc(src) ?? src : "",
        alt: typeof alt === "string" ? alt : "",
        title: typeof caption === "string" ? caption : null,
      },
    };
  }

  if (block.content || block.attrs || block.marks || block.type === "heading" || block.type?.includes("List")) {
    return {
      ...block,
      content: block.content?.map(blockToTipTapNode),
    } as JSONContent;
  }

  if (block.type === "paragraph") {
    return {
      type: "paragraph",
      content: block.text ? [{ type: "text", text: block.text }] : [],
    };
  }

  return block as JSONContent;
}

function contentBlocksToTipTapDoc(contentBlocks: AdminArticleContentBlocks): JSONContent {
  if (!Array.isArray(contentBlocks) && contentBlocks.type === "doc") {
    return blockToTipTapNode(contentBlocks);
  }

  const content = Array.isArray(contentBlocks)
    ? contentBlocks.map((block) => blockToTipTapNode(block as JSONContent))
    : [blockToTipTapNode(contentBlocks as JSONContent)];

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

function tipTapDocToStoredContent(doc: JSONContent): AdminArticleContentBlocks {
  return normalizeStoredImageNode({
    ...doc,
    type: "doc",
    content: (doc.content ?? []).filter((node) => node.type !== "paragraph" || extractText(node).trim() || node.content?.length),
  }) as AdminArticleContentBlocks;
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

function activeTextBlock(editor: Editor | null) {
  if (!editor) return "paragraph";
  return editor.isActive("heading") ? "heading" : "paragraph";
}

function activeBlockValue(editor: Editor | null, key: "fontSize" | "lineHeight") {
  if (!editor) return "";
  const block = activeTextBlock(editor);
  const value = editor.getAttributes(block)[key];
  return typeof value === "string" ? value : "";
}

function updateBlockStyle(editor: Editor | null, key: "fontSize" | "lineHeight", value: string) {
  if (!editor) return;
  const attrs = { [key]: value || null };
  const block = activeTextBlock(editor);
  editor.chain().focus().updateAttributes(block, attrs).run();
}

function EditorToolbar({ editor, onImageUpload, disabled }: { editor: Editor | null; onImageUpload: (event: ChangeEvent<HTMLInputElement>) => void; disabled: boolean }) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 p-3 text-slate-600">
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleBulletList().run()} className={toolbarButtonClass(editor?.isActive("bulletList"))} aria-label="Bullet list"><List size={18} /></button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()} className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${editor?.isActive("heading", { level: 1 }) ? "bg-violet-100 text-violet-700" : "hover:bg-white"}`}>H1</button>
      <button type="button" disabled={disabled || !editor} onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${editor?.isActive("heading", { level: 2 }) ? "bg-violet-100 text-violet-700" : "hover:bg-white"}`}>H2</button>
      <span className="h-7 w-px bg-slate-200" />
      <select
        disabled={disabled || !editor}
        value={activeBlockValue(editor, "fontSize")}
        onChange={(event) => updateBlockStyle(editor, "fontSize", event.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-violet-400 focus:ring-4 focus:ring-violet-100 disabled:opacity-60"
        aria-label="Font size"
      >
        {fontSizeOptions.map((option) => <option key={option.label} value={option.value}>{option.label}</option>)}
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
      <select
        disabled={disabled || !editor}
        value={activeBlockValue(editor, "lineHeight")}
        onChange={(event) => updateBlockStyle(editor, "lineHeight", event.target.value)}
        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-violet-400 focus:ring-4 focus:ring-violet-100 disabled:opacity-60"
        aria-label="Line spacing"
      >
        {spacingOptions.map((option) => <option key={option.label} value={option.value}>{option.label}</option>)}
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
  onSave: (contentBlocks: AdminArticleContentBlocks) => Promise<void>;
  saving: boolean;
}) {
  const [formError, setFormError] = useState("");
  const [uploading, setUploading] = useState(false);
  const disabled = saving || uploading;
  const editor = useEditor({
    extensions: [
      StarterKit,
      UnderlineExtension,
      RichTextBlockStyle,
      Image.configure({ inline: false, allowBase64: false }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
    ],
    content: contentBlocksToTipTapDoc(form.contentBlocks),
    editorProps: {
      attributes: {
        class: "min-h-80 px-7 py-6 text-lg leading-8 text-slate-950 outline-none prose prose-slate max-w-none [&_img]:mx-auto [&_img]:my-6 [&_img]:max-h-80 [&_img]:rounded-2xl [&_img]:object-cover",
      },
    },
    onUpdate: ({ editor: updatedEditor }: { editor: Editor }) => {
      setForm((current) => ({
        ...current,
        contentBlocks: tipTapDocToStoredContent(updatedEditor.getJSON()),
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
    const currentBlocks = editor ? tipTapDocToStoredContent(editor.getJSON()) : form.contentBlocks;
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
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("published-desc");
  const [editorMode, setEditorMode] = useState<"list" | "new" | "edit">("list");
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [form, setForm] = useState<ArticleForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [saving, setSaving] = useState(false);
  const [deletingArticle, setDeletingArticle] = useState<Article | null>(null);
  const [page, setPage] = useState(1);
  const mobileList = useMobileListView();

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

  const visibleArticles = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const filtered = articles.filter((article) => {
      const matchesCategory = selectedCategory === "All" || article.category === selectedCategory;
      const matchesSearch = !normalizedSearch || article.title.toLowerCase().includes(normalizedSearch);
      return matchesCategory && matchesSearch;
    });

    return [...filtered].sort((left, right) => {
      switch (sortBy) {
        case "published-asc":
          return new Date(left.publishedAt ?? 0).getTime() - new Date(right.publishedAt ?? 0).getTime();
        case "views-desc":
          return right.views - left.views;
        case "likes-desc":
          return right.likes - left.likes;
        case "saves-desc":
          return right.saves - left.saves;
        case "published-desc":
        default:
          return new Date(right.publishedAt ?? 0).getTime() - new Date(left.publishedAt ?? 0).getTime();
      }
    });
  }, [articles, searchTerm, selectedCategory, sortBy]);
  const totalPages = Math.max(1, Math.ceil(visibleArticles.length / PAGE_SIZE));
  const pageArticles = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return visibleArticles.slice(start, start + PAGE_SIZE);
  }, [page, visibleArticles]);

  useEffect(() => {
    setPage(1);
  }, [searchTerm, selectedCategory, sortBy]);

  useEffect(() => {
    setPage((current) => Math.min(current, totalPages));
  }, [totalPages]);

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

  async function saveNewArticle(contentBlocks: AdminArticleContentBlocks) {
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

  async function saveEditedArticle(contentBlocks: AdminArticleContentBlocks) {
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

  async function confirmDeleteArticle() {
    if (!deletingArticle) return;
    setSaving(true);
    try {
      await deleteAdminArticle(deletingArticle.id);
      setArticles((current) => current.filter((item) => item.id !== deletingArticle.id));
      setDeletingArticle(null);
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
    <section className="px-5 pb-5 pt-20 sm:p-8 lg:p-12">
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

      <div className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px] lg:items-end">
        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-slate-600">Search articles by title</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} aria-hidden="true" />
            <input
              type="search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Enter an article title"
              className="w-full rounded-2xl border border-slate-200 bg-white py-3.5 pl-12 pr-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
            />
          </span>
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-semibold text-slate-600">Sort articles</span>
          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value as SortOption)}
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3.5 font-semibold text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        {categories.map((category) => (
          <button key={category} type="button" onClick={() => setSelectedCategory(category)} className={`rounded-full px-5 py-2.5 text-sm font-semibold transition ${selectedCategory === category ? "bg-indigo-500 text-white shadow-sm" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
            {category}
          </button>
        ))}
      </div>

      <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {!mobileList && <div className="grid grid-cols-[minmax(280px,1.9fr)_minmax(120px,0.75fr)_minmax(110px,0.75fr)_minmax(120px,0.75fr)_minmax(78px,0.45fr)_minmax(78px,0.45fr)_minmax(78px,0.45fr)_minmax(160px,0.85fr)] border-b border-slate-200 bg-slate-50/70 px-5 py-5 text-xs font-bold uppercase tracking-wide text-slate-500">
          <div>Article</div>
          <div>Category</div>
          <div>Status</div>
          <div>Published</div>
          <div>Views</div>
          <div>Likes</div>
          <div>Saves</div>
          <div>Actions</div>
        </div>}

        {loading && <div className="px-6 py-16 text-center text-slate-500">Loading articles...</div>}

        {!loading && pageArticles.map((article) => (
          !mobileList && <article key={article.id} className="grid grid-cols-[minmax(280px,1.9fr)_minmax(120px,0.75fr)_minmax(110px,0.75fr)_minmax(120px,0.75fr)_minmax(78px,0.45fr)_minmax(78px,0.45fr)_minmax(78px,0.45fr)_minmax(160px,0.85fr)] items-center gap-0 border-b border-slate-200 px-5 py-6 transition last:border-b-0 hover:bg-slate-50/70">
            <div className="flex min-w-0 gap-3 pr-4">
              <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-xl border border-slate-200 bg-slate-100 text-slate-300">
                {article.coverImageUrl ? <img src={imageSrc(article.coverImageUrl) ?? undefined} alt="" className="h-full w-full object-cover" /> : <ImageIcon size={24} />}
              </div>
              <div className="min-w-0">
                <h2 className="line-clamp-2 font-bold leading-snug text-slate-900">{article.title}</h2>
                <p className="mt-1 line-clamp-2 text-sm leading-5 text-slate-500">{shortText(article.summary, 48)}</p>
                <p className="mt-1 truncate text-xs font-semibold text-slate-300">{article.sourceName}</p>
              </div>
            </div>
            <div><span className={`inline-flex max-w-[7rem] truncate rounded-full px-3 py-1 text-sm font-medium ${categoryTone(article.category)}`}>{article.category}</span></div>
            <div><span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">Published</span></div>
            <div className="text-sm text-slate-500">{formatPublishedDate(article.publishedAt)}</div>
            <div className="text-sm text-slate-600"><span className="inline-flex items-center gap-1.5"><Eye size={16} className="text-slate-400" />{article.views.toLocaleString()}</span></div>
            <div className="text-sm text-slate-600"><span className="inline-flex items-center gap-1.5"><Heart size={16} className="text-red-500" />{article.likes.toLocaleString()}</span></div>
            <div className="text-sm text-slate-600"><span className="inline-flex items-center gap-1.5"><Bookmark size={16} className="text-indigo-500" />{article.saves.toLocaleString()}</span></div>
            <div className="flex items-center gap-3 whitespace-nowrap">
              <button type="button" disabled={saving} onClick={() => void openEditArticle(article)} className="inline-flex items-center gap-1.5 font-semibold text-indigo-600 hover:text-indigo-800 disabled:opacity-60">
                <Pencil size={17} /> Edit
              </button>
              <button type="button" disabled={saving} onClick={() => setDeletingArticle(article)} className="inline-flex items-center gap-1.5 font-semibold text-red-500 hover:text-red-700 disabled:opacity-60">
                <Trash2 size={17} /> Delete
              </button>
            </div>
          </article>
        ))}

        {!loading && mobileList && pageArticles.length > 0 && (
          <div className="divide-y divide-slate-200">
            {pageArticles.map((article) => (
              <article key={article.id} className="p-5">
                <div className="flex gap-4">
                  <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-xl border border-slate-200 bg-slate-100 text-slate-300">
                    {article.coverImageUrl ? <img src={imageSrc(article.coverImageUrl) ?? undefined} alt="" className="h-full w-full object-cover" /> : <ImageIcon size={24} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="line-clamp-2 font-bold leading-snug text-slate-900">{article.title}</h2>
                    <p className="mt-1 line-clamp-2 text-sm leading-5 text-slate-500">{shortText(article.summary, 68)}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className={`inline-flex max-w-full truncate rounded-full px-3 py-1 text-xs font-semibold ${categoryTone(article.category)}`}>{article.category}</span>
                      <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Published</span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 rounded-xl bg-slate-50 px-3 py-3 text-center text-xs font-semibold text-slate-600">
                  <span className="inline-flex items-center justify-center gap-1"><Eye size={14} className="text-slate-400" />{article.views.toLocaleString()}</span>
                  <span className="inline-flex items-center justify-center gap-1"><Heart size={14} className="text-red-500" />{article.likes.toLocaleString()}</span>
                  <span className="inline-flex items-center justify-center gap-1"><Bookmark size={14} className="text-indigo-500" />{article.saves.toLocaleString()}</span>
                </div>
                <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-500">
                  <span>{formatPublishedDate(article.publishedAt)}</span>
                  <span className="truncate">{article.sourceName}</span>
                </div>
                <div className="mt-5 grid grid-cols-2 gap-3">
                  <button type="button" disabled={saving} onClick={() => void openEditArticle(article)} className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-indigo-200 px-4 py-2.5 text-sm font-semibold text-indigo-600 hover:bg-indigo-50 disabled:opacity-60">
                    <Pencil size={16} /> Edit
                  </button>
                  <button type="button" disabled={saving} onClick={() => setDeletingArticle(article)} className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-red-200 px-4 py-2.5 text-sm font-semibold text-red-500 hover:bg-red-50 disabled:opacity-60">
                    <Trash2 size={16} /> Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}

        {!loading && visibleArticles.length === 0 && !pageError && (
          <div className="px-6 py-16 text-center text-slate-500">No published articles match the current filters.</div>
        )}

        {!loading && visibleArticles.length > PAGE_SIZE && (
          <div className="flex flex-col gap-3 border-t border-slate-200 px-5 py-4 text-sm sm:flex-row sm:items-center sm:justify-between">
            <span className="text-slate-500">Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, visibleArticles.length)} of {visibleArticles.length} articles</span>
            <div className="grid grid-cols-2 gap-3 sm:flex">
              <button type="button" disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Previous</button>
              <button type="button" disabled={page === totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Next</button>
            </div>
          </div>
        )}
      </div>
      {deletingArticle && (
        <Modal title="Delete Article" onClose={() => !saving && setDeletingArticle(null)}>
          <p className="text-sm leading-6 text-slate-600">
            Are you sure you want to delete <strong className="text-slate-900">{deletingArticle.title}</strong>? This action cannot be undone.
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-2">
            <button type="button" disabled={saving} onClick={() => void confirmDeleteArticle()} className="rounded-xl bg-red-600 px-5 py-3 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60">
              {saving ? "Deleting..." : "Delete Article"}
            </button>
            <button type="button" disabled={saving} onClick={() => setDeletingArticle(null)} className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold hover:bg-slate-50 disabled:opacity-60">
              Cancel
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}
