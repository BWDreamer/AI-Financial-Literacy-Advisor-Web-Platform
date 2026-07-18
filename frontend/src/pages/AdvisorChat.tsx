import { ChangeEvent, DragEvent, FormEvent, KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileText, PanelLeft, Plus, Send, Trash2, X } from "lucide-react";
import { ChatMessage, Conversation, ConversationDetail, addConversationMessage, createConversation, deleteConversation, getConversation, getConversations, sendAdvisorMessage, sendAdvisorPdfMessage } from "../api/chat";
import {
  GOAL_PLANNING_START_MESSAGE,
  GoalCategoryGrid,
  GoalPlanningEntryButton,
  getGoalPlanningUiState,
  goalCategoryPrompt,
  visibleChatMessage,
  type GoalCategoryId,
} from "../components/chat/GoalPlanningControls";
import FormattedChatMessage from "../components/chat/FormattedChatMessage";
import { useUser } from "../store/UserProvider";

type AttachmentPreview = { id: string; name: string; extension: string; isImage: boolean; file: File; dataUrl?: string };
type LocalAttachmentMap = Record<number, AttachmentPreview[]>;

function sortedConversations(items: Conversation[]) {
  return [...items].sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime());
}

function fileExtension(file: File) {
  return (file.name.split(".").pop() || "File").toUpperCase();
}

function readImage(file: File) {
  return new Promise<string>((resolve) => {
    const reader = new FileReader(); reader.onload = () => resolve(String(reader.result || "")); reader.onerror = () => resolve(""); reader.readAsDataURL(file);
  });
}

function HistoryItem({ item, activeId, onSelect, onDelete }: { item: Conversation; activeId?: number; onSelect: () => void; onDelete: () => void }) {
  return <button type="button" onClick={onSelect} title={item.title} className={`group flex w-full items-center gap-3 rounded-2xl p-3 text-left transition ${activeId === item.conversation_id ? "bg-blue-50 text-slate-900" : "text-slate-600 hover:bg-slate-50"}`}><span className="min-w-0 flex-1 truncate text-sm font-semibold">{item.title}</span><span onClick={(event) => { event.stopPropagation(); onDelete(); }} className="grid size-8 shrink-0 place-items-center rounded-xl text-red-500 hover:bg-red-50"><Trash2 size={16} /></span></button>;
}

function ConversationSidebar({ conversations, activeId, onNew, onSelect, onDelete }: { conversations: Conversation[]; activeId?: number; onNew: () => void; onSelect: (id: number) => void; onDelete: (id: number) => void }) {
  return <aside className="sticky top-0 h-screen w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4"><button type="button" onClick={onNew} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white"><Plus size={18} />New Conversation</button><p className="mt-5 px-1 text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Historical Conversation</p><div className="mt-3 space-y-2">{conversations.length === 0 && <p className="p-3 text-sm text-slate-500">No saved conversations.</p>}{conversations.map((item) => <HistoryItem key={item.conversation_id} item={item} activeId={activeId} onSelect={() => onSelect(item.conversation_id)} onDelete={() => onDelete(item.conversation_id)} />)}</div></aside>;
}

function EmptyConversationWelcome({ userName }: { userName: string }) {
  return (
    <div className="grid min-h-0 flex-1 place-items-center px-4 py-12 text-center">
      <h2 className="text-3xl font-extrabold tracking-tight text-slate-950 sm:text-4xl">
        How can I help, <span className="text-slate-950">{userName}</span>?
      </h2>
    </div>
  );
}

function MessageList({ messages, attachments, sending, userName, onSelectGoalCategory }: { messages: ChatMessage[]; attachments: LocalAttachmentMap; sending: boolean; userName: string; onSelectGoalCategory: (categoryId: GoalCategoryId) => void }) {
  if (messages.length === 0) {
    return <EmptyConversationWelcome userName={userName} />;
  }

  const planningState = getGoalPlanningUiState(messages);
  return (
    <div className="mt-8 flex-1 space-y-4 overflow-y-auto pr-1">
      {messages.map((message) => {
        const content = visibleChatMessage(message.content);
        return (
          <div key={message.id}>
            <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <article
                style={{ maxWidth: "61.8%" }}
                className={`inline-block w-fit rounded-2xl p-4 ${message.role === "user" ? "bg-blue-600 text-white" : "bg-white shadow-sm"}`}
              >
                <MessageAttachments files={attachments[message.id] || []} inBubble />
                {content && message.role === "user" && (
                  <p className="max-w-full whitespace-pre-wrap break-words text-sm leading-6">
                    {content}
                  </p>
                )}
                {content && message.role === "assistant" && (
                  <FormattedChatMessage content={content} />
                )}
              </article>
            </div>
            {message.id === planningState.startMessageId
              && planningState.showCategoryOptions && (
                <GoalCategoryGrid
                  disabled={sending}
                  selectedCategory={planningState.selectedCategory}
                  onSelect={onSelectGoalCategory}
                />
              )}
          </div>
        );
      })}
    </div>
  );
}

function isImageFile(file: File) {
  return file.type.startsWith("image/") || /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(file.name);
}

function removeOnKey(event: KeyboardEvent, onRemove?: () => void) {
  if (!onRemove || (event.key !== "Delete" && event.key !== "Backspace")) return;
  event.preventDefault(); onRemove();
}

function AttachmentCard({ file, onRemove, inBubble = false }: { file: AttachmentPreview; onRemove?: () => void; inBubble?: boolean }) {
  const fileBg = inBubble ? "bg-white/95 text-slate-900" : "bg-slate-50 text-slate-900";
  if (file.isImage && file.dataUrl) return <div tabIndex={onRemove ? 0 : -1} onKeyDown={(event) => removeOnKey(event, onRemove)} className="group relative size-20 shrink-0 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-100"><div className="size-20 overflow-hidden rounded-2xl bg-slate-100 ring-1 ring-slate-200"><img src={file.dataUrl} alt={file.name} className="block size-full object-cover" /></div>{onRemove && <button type="button" aria-label={`Delete ${file.name}`} onClick={onRemove} className="absolute right-1 top-1 z-20 grid size-6 place-items-center rounded-full bg-slate-800 text-white shadow-md ring-2 ring-white hover:bg-red-500"><X size={14} strokeWidth={3} /></button>}</div>;
  return <div tabIndex={onRemove ? 0 : -1} onKeyDown={(event) => removeOnKey(event, onRemove)} className={`relative flex min-w-44 items-center gap-3 rounded-2xl p-3 focus:outline-none focus:ring-4 focus:ring-blue-100 ${fileBg}`}><span className="grid size-10 place-items-center rounded-xl bg-red-500 text-white"><FileText size={20} /></span><span className="min-w-0"><span className="block truncate text-sm font-bold">{file.name}</span><span className="text-xs uppercase text-slate-500">{file.extension}</span></span>{onRemove && <button type="button" aria-label={`Delete ${file.name}`} onClick={onRemove} className="absolute right-1 top-1 z-20 grid size-6 place-items-center rounded-full bg-slate-800 text-white shadow-md ring-2 ring-white hover:bg-red-500"><X size={14} strokeWidth={3} /></button>}</div>;
}

function MessageAttachments({ files, onRemove, inBubble = false }: { files: AttachmentPreview[]; onRemove?: (index: number) => void; inBubble?: boolean }) {
  if (!files.length) return null;
  return <div className={`flex flex-wrap items-start gap-3 ${inBubble ? "mb-3" : "px-2 pb-4"}`}>{files.map((file, index) => <AttachmentCard key={file.id} file={file} inBubble={inBubble} onRemove={onRemove ? () => onRemove(index) : undefined} />)}</div>;
}

function ChatComposer({ sending, onSubmit }: { sending: boolean; onSubmit: (message: string, files: AttachmentPreview[]) => Promise<void> }) {
  const [message, setMessage] = useState(""); const [files, setFiles] = useState<AttachmentPreview[]>([]); const [dragging, setDragging] = useState(false); const inputRef = useRef<HTMLInputElement>(null); const textRef = useRef<HTMLTextAreaElement>(null);
  const canSend = (message.trim().length > 0 || files.length > 0) && !sending;
  async function addFiles(list?: FileList | null) {
    if (!list) return; const previews = await Promise.all(Array.from(list).map(toPreview));
    setFiles((current) => [...current, ...previews]);
  }
  useEffect(() => { if (textRef.current) { textRef.current.style.height = "auto"; textRef.current.style.height = `${Math.min(textRef.current.scrollHeight, 220)}px`; } }, [message]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!canSend) return;
    await onSubmit(message.trim(), files); setMessage(""); setFiles([]); if (inputRef.current) inputRef.current.value = "";
  }
  function removeLastOnEmpty(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (message || !files.length || (event.key !== "Delete" && event.key !== "Backspace")) return;
    event.preventDefault(); setFiles((current) => current.slice(0, -1));
  }
  function drop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault(); setDragging(false); void addFiles(event.dataTransfer.files);
  }
  return <form onSubmit={submit} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={drop} className={`rounded-3xl border bg-white p-3 shadow-sm transition ${dragging ? "border-blue-400 ring-4 ring-blue-100" : "border-slate-200"}`}><MessageAttachments files={files} onRemove={(index) => setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))} /><textarea ref={textRef} value={message} onKeyDown={removeLastOnEmpty} onChange={(event) => setMessage(event.target.value)} rows={1} placeholder="Ask anything about personal finance..." className={`max-h-56 w-full resize-none overflow-y-auto bg-transparent px-2 text-sm leading-6 outline-none placeholder:text-slate-400 ${files.length ? "min-h-16" : "min-h-12"}`} /><div className="mt-2 flex items-center justify-between"><input ref={inputRef} type="file" multiple accept=".pdf,application/pdf" className="hidden" onChange={(event: ChangeEvent<HTMLInputElement>) => void addFiles(event.target.files)} /><button type="button" onClick={() => inputRef.current?.click()} className="grid size-10 place-items-center rounded-full text-slate-600 hover:bg-slate-100" title="Upload PDF financial documents"><Plus size={24} /></button><button type="submit" disabled={!canSend} className={`grid size-10 place-items-center rounded-full transition ${canSend ? "bg-blue-600 text-white hover:bg-blue-700" : "bg-slate-200 text-slate-400"}`} title="Send message"><Send size={18} /></button></div></form>;
}

async function toPreview(file: File): Promise<AttachmentPreview> {
  const isImage = isImageFile(file);
  return { id: crypto.randomUUID(), name: file.name, extension: fileExtension(file), isImage, file, dataUrl: isImage ? await readImage(file) : undefined };
}

export default function AdvisorChat() {
  const { user } = useUser();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [localAttachments, setLocalAttachments] = useState<LocalAttachmentMap>({});
  const [draftConversationId, setDraftConversationId] = useState<number | null>(null);
  const userName = user?.username?.trim()
    || user?.email.split("@")[0]
    || "there";
  const orderedConversations = useMemo(
    () => sortedConversations(conversations).filter(
      (item) => item.conversation_id !== draftConversationId,
    ),
    [conversations, draftConversationId],
  );
  const loadList = useCallback(async () => {
    const items = sortedConversations(await getConversations());
    setConversations(items);
    return items;
  }, []);

  useEffect(() => {
    loadList()
      .then(async (items) => {
        if (items[0]) {
          setActive(await getConversation(items[0].conversation_id));
        }
      })
      .catch((caught) => setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load conversations.",
      ))
      .finally(() => setLoading(false));
  }, [loadList]);

  async function selectConversation(id: number) {
    setError("");
    setDraftConversationId(null);
    try {
      setActive(await getConversation(id));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load this conversation.",
      );
    }
  }

  function startConversation() {
    setError("");
    setDraftConversationId(null);
    setActive(null);
  }

  async function removeConversation(id: number) {
    await deleteConversation(id);
    const items = await loadList();
    setActive(
      items[0]
        ? await getConversation(items[0].conversation_id)
        : null,
    );
  }

  function attachToLatestUserMessage(next: ConversationDetail, files: AttachmentPreview[]) {
    const userMessages = next.messages.filter((item) => item.role === "user");
    const latest = userMessages[userMessages.length - 1]; if (!latest || !files.length) return;
    setLocalAttachments((current) => ({ ...current, [latest.id]: files }));
  }

  async function refreshActiveConversation(
    conversationId: number,
    files: AttachmentPreview[] = [],
  ) {
    const next = await getConversation(conversationId);
    attachToLatestUserMessage(next, files);
    setDraftConversationId(conversationId);
    setActive(next);
    await loadList();
  }

  async function sendMessage(message: string, files: AttachmentPreview[]) {
    setSending(true);
    setError("");
    try {
      const conversation = active || {
        ...(await createConversation()),
        messages: [],
      };
      if (files.length) {
        await sendAdvisorPdfMessage(
          message || "Extract financial information from the uploaded PDF.",
          conversation.conversation_id,
          files.map((item) => item.file),
        );
      } else {
        await sendAdvisorMessage(message, conversation.conversation_id);
      }
      await refreshActiveConversation(conversation.conversation_id, files);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to send your message.",
      );
    } finally {
      setSending(false);
    }
  }

  async function appendGoalPlanningPrompt(content: string) {
    setSending(true);
    setError("");
    try {
      const conversation = active || {
        ...(await createConversation()),
        messages: [],
      };
      await addConversationMessage(
        conversation.conversation_id,
        "assistant",
        content,
      );
      await refreshActiveConversation(conversation.conversation_id);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to start goal planning.",
      );
    } finally {
      setSending(false);
    }
  }

  function startGoalPlanning() {
    void appendGoalPlanningPrompt(GOAL_PLANNING_START_MESSAGE);
  }

  function selectGoalCategory(categoryId: GoalCategoryId) {
    void appendGoalPlanningPrompt(goalCategoryPrompt(categoryId));
  }

  if (loading) {
    return <main className="p-10 text-slate-500">Loading conversations...</main>;
  }

  return (
    <main className="flex min-h-screen bg-slate-50">
      {historyOpen && (
        <ConversationSidebar
          conversations={orderedConversations}
          activeId={active?.conversation_id}
          onNew={startConversation}
          onSelect={(id) => void selectConversation(id)}
          onDelete={(id) => void removeConversation(id)}
        />
      )}
      <section className="flex min-w-0 flex-1 flex-col p-5 sm:p-8">
        <div className="flex flex-wrap items-start gap-4">
          <button
            type="button"
            aria-label="Toggle conversation history"
            onClick={() => setHistoryOpen(!historyOpen)}
            className="grid size-11 shrink-0 place-items-center rounded-full bg-white text-slate-600 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-blue-100"
          >
            <PanelLeft size={22} aria-hidden="true" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-bold tracking-tight">Advisor Chat</h1>
            <p className="mt-2 text-slate-500">
              Ask educational questions about personal finance.
            </p>
          </div>
          <GoalPlanningEntryButton
            disabled={sending}
            onClick={startGoalPlanning}
          />
        </div>
        {error && (
          <p className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <MessageList
          messages={active?.messages || []}
          attachments={localAttachments}
          sending={sending}
          userName={userName}
          onSelectGoalCategory={selectGoalCategory}
        />
        <div className="mt-6">
          <ChatComposer sending={sending} onSubmit={sendMessage} />
        </div>
      </section>
    </main>
  );
}
