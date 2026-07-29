import { ChangeEvent, DragEvent, FormEvent, KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, FileText, PanelLeft, Plus, Send, Trash2, X } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChatMessage, Conversation, ConversationDetail, addConversationMessage, createConversation, deleteConversation, getConversation, getConversations, sendAdvisorPdfMessage, streamAdvisorMessage } from "../api/chat";
import {
  GOAL_PLANNING_START_MESSAGE,
  GoalCategoryGrid,
  GoalPlanningEntryButton,
  getGoalPlanningUiState,
  goalCategoryPrompt,
  visibleChatMessage,
  type GoalCategoryId,
} from "../components/chat/GoalPlanningControls";
import GoalReviewCard, {
  parseGoalReviewMessage,
  type GoalReviewCardData,
} from "../components/chat/GoalReviewCard";
import FormattedChatMessage from "../components/chat/FormattedChatMessage";
import MemoryUpdateToast from "../components/chat/MemoryUpdateToast";
import SuggestedQuestions, { rememberSuggestedQuestions, selectSuggestedQuestions } from "../components/chat/SuggestedQuestions";
import { useUser } from "../store/UserProvider";

type AttachmentPreview = { id: string; name: string; extension: string; isImage: boolean; file: File; dataUrl?: string };
type LocalAttachmentMap = Record<number, AttachmentPreview[]>;
type PendingExchange = {
  conversationId: number | null;
  userContent: string;
  files: AttachmentPreview[];
  assistantContent: string;
  thinking: boolean;
};
type GoalReviewRouteState = {
  mode: "goal-review";
  requestId: string;
  goal: GoalReviewCardData;
};

const handledGoalReviewRequests = new Set<string>();

function goalReviewRouteState(value: unknown): GoalReviewRouteState | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as Record<string, unknown>;
  if (
    candidate.mode !== "goal-review"
    || typeof candidate.requestId !== "string"
    || !candidate.goal
    || typeof candidate.goal !== "object"
  ) {
    return null;
  }
  const goal = candidate.goal as Partial<GoalReviewCardData>;
  if (
    goal.kind !== "goal_review"
    || goal.version !== 1
    || typeof goal.goal_id !== "number"
    || typeof goal.name !== "string"
  ) {
    return null;
  }
  return candidate as GoalReviewRouteState;
}

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

function HistoryItem({ item, activeId, disabled, onSelect, onDelete }: { item: Conversation; activeId?: number; disabled: boolean; onSelect: () => void; onDelete: () => void }) {
  return <button type="button" disabled={disabled} onClick={onSelect} title={item.title} className={`group flex w-full items-center gap-3 rounded-2xl p-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${activeId === item.conversation_id ? "bg-blue-50 text-slate-900" : "text-slate-600 hover:bg-slate-50"}`}><span className="min-w-0 flex-1 truncate text-sm font-semibold">{item.title}</span><span role="button" tabIndex={disabled ? -1 : 0} aria-label={`Delete ${item.title}`} onClick={(event) => { event.stopPropagation(); if (!disabled) onDelete(); }} onKeyDown={(event) => { if (disabled || (event.key !== "Enter" && event.key !== " ")) return; event.preventDefault(); event.stopPropagation(); onDelete(); }} className="grid size-8 shrink-0 place-items-center rounded-xl text-red-500 hover:bg-red-50"><Trash2 size={16} /></span></button>;
}

function ConversationSidebar({ conversations, activeId, disabled, mobile = false, open = true, onClose, onNew, onSelect, onDelete }: { conversations: Conversation[]; activeId?: number; disabled: boolean; mobile?: boolean; open?: boolean; onClose?: () => void; onNew: () => void; onSelect: (id: number) => void; onDelete: (id: number) => void }) {
  const content = <><button type="button" disabled={disabled} onClick={() => { onNew(); onClose?.(); }} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"><Plus size={18} />New Conversation</button><p className="mt-5 px-1 text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Historical Conversation</p><div className="mt-3 space-y-2">{conversations.length === 0 && <p className="p-3 text-sm text-slate-500">No saved conversations.</p>}{conversations.map((item) => <HistoryItem key={item.conversation_id} item={item} activeId={activeId} disabled={disabled} onSelect={() => { onSelect(item.conversation_id); onClose?.(); }} onDelete={() => onDelete(item.conversation_id)} />)}</div></>;
  if (mobile) return <aside className={`fixed inset-y-0 left-0 z-50 w-[82vw] max-w-80 overflow-y-auto border-r border-slate-200 bg-white p-4 transition-transform duration-[650ms] ease-out lg:hidden ${open ? "translate-x-0" : "-translate-x-full"}`}><div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-bold text-slate-900">Conversations</h2><button type="button" onClick={onClose} className="grid size-9 place-items-center rounded-lg text-slate-500 hover:bg-slate-100" aria-label="Close conversations"><X size={20} /></button></div>{content}</aside>;
  return <aside className="sticky top-0 hidden h-screen w-64 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-4 lg:block">{content}</aside>;
}

function MobileHistoryHandle({ open, onClick }: { open: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} style={{ left: open ? "min(82vw, 20rem)" : 0 }} className="fixed top-1/2 z-[55] flex h-28 w-10 -translate-y-1/2 items-center justify-center rounded-r-xl bg-blue-600 text-[11px] font-bold uppercase tracking-[0.16em] text-white shadow-lg transition-[left,background-color] duration-[650ms] ease-out hover:bg-blue-700 lg:hidden" aria-label={open ? "Close conversation history" : "Open conversation history"}>
    <span className="flex -rotate-90 items-center gap-1">History<ChevronDown size={14} className={`transition-transform ${open ? "rotate-180" : ""}`} /></span>
  </button>;
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

function MessageList({ messages, attachments, pending, sending, userName, pendingGoalReview, onSelectGoalCategory }: { messages: ChatMessage[]; attachments: LocalAttachmentMap; pending: PendingExchange | null; sending: boolean; userName: string; pendingGoalReview: GoalReviewCardData | null; onSelectGoalCategory: (categoryId: GoalCategoryId) => void }) {
  const messageEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, pending?.assistantContent, pending?.thinking, pendingGoalReview]);

  if (messages.length === 0 && !pending && !pendingGoalReview) {
    return <EmptyConversationWelcome userName={userName} />;
  }

  const planningState = getGoalPlanningUiState(messages);
  return (
    <div className="mt-8 flex-1 space-y-4 overflow-y-auto pr-1">
      {messages.map((message) => {
        const goalReview = message.role === "user"
          ? parseGoalReviewMessage(message.content)
          : null;
        const content = goalReview ? "" : visibleChatMessage(message.content);
        return (
          <div key={message.id}>
            <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <article
                style={goalReview ? undefined : { maxWidth: "61.8%" }}
                className={goalReview
                  ? "w-full max-w-2xl"
                  : `inline-block w-fit rounded-2xl p-4 ${message.role === "user" ? "bg-blue-600 text-white" : "bg-white shadow-sm"}`}
              >
                {goalReview && <GoalReviewCard goal={goalReview} />}
                {!goalReview && <MessageAttachments files={attachments[message.id] || []} inBubble />}
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
      {pendingGoalReview && (
        <div className="flex justify-end">
          <div className="w-full max-w-2xl">
            <GoalReviewCard goal={pendingGoalReview} pending />
          </div>
        </div>
      )}
      {pending && (
        <div className="space-y-4" aria-busy={pending.thinking}>
          {!pendingGoalReview && (
            <div className="flex justify-end">
              <article
                style={{ maxWidth: "61.8%" }}
                className="inline-block w-fit rounded-2xl bg-blue-600 p-4 text-white"
              >
                <MessageAttachments files={pending.files} inBubble />
                {pending.userContent && (
                  <p className="max-w-full whitespace-pre-wrap break-words text-sm leading-6">
                    {pending.userContent}
                  </p>
                )}
              </article>
            </div>
          )}
          <div className="flex justify-start">
            <article
              style={{ maxWidth: "61.8%" }}
              className="inline-block min-w-28 w-fit rounded-2xl bg-white p-4 shadow-sm"
            >
              {pending.thinking ? (
                <p role="status" aria-label="AI is thinking" className="text-sm font-bold leading-6">
                  <span className="thinking-shimmer">Thinking</span>
                </p>
              ) : (
                <FormattedChatMessage content={pending.assistantContent} />
              )}
            </article>
          </div>
        </div>
      )}
      <div ref={messageEndRef} aria-hidden="true" />
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

function ChatComposer({ sending, onSubmit, onSetGoal }: { sending: boolean; onSubmit: (message: string, files: AttachmentPreview[]) => Promise<void>; onSetGoal: () => void }) {
  const [message, setMessage] = useState(""); const [files, setFiles] = useState<AttachmentPreview[]>([]); const [dragging, setDragging] = useState(false); const inputRef = useRef<HTMLInputElement>(null); const textRef = useRef<HTMLTextAreaElement>(null);
  const canSend = (message.trim().length > 0 || files.length > 0) && !sending;
  async function addFiles(list?: FileList | null) {
    if (!list) return; const previews = await Promise.all(Array.from(list).map(toPreview));
    setFiles((current) => [...current, ...previews]);
  }
  useEffect(() => { if (textRef.current) { textRef.current.style.height = "auto"; textRef.current.style.height = `${Math.min(textRef.current.scrollHeight, 220)}px`; } }, [message]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!canSend) return;
    const submittedMessage = message.trim(); const submittedFiles = files;
    setMessage(""); setFiles([]); if (inputRef.current) inputRef.current.value = "";
    await onSubmit(submittedMessage, submittedFiles);
  }
  function removeLastOnEmpty(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (message || !files.length || (event.key !== "Delete" && event.key !== "Backspace")) return;
    event.preventDefault(); setFiles((current) => current.slice(0, -1));
  }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault(); event.currentTarget.form?.requestSubmit(); return;
    }
    removeLastOnEmpty(event);
  }
  function drop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault(); setDragging(false); void addFiles(event.dataTransfer.files);
  }
  return <form onSubmit={submit} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={drop} className={`rounded-3xl border bg-white p-3 shadow-sm transition ${dragging ? "border-blue-400 ring-4 ring-blue-100" : "border-slate-200"}`}><MessageAttachments files={files} onRemove={(index) => setFiles((current) => current.filter((_, itemIndex) => itemIndex !== index))} /><textarea ref={textRef} value={message} onKeyDown={keyDown} onChange={(event) => setMessage(event.target.value)} rows={1} placeholder="Ask anything about personal finance..." className={`max-h-56 w-full resize-none overflow-y-auto bg-transparent px-2 text-sm leading-6 outline-none placeholder:text-slate-400 ${files.length ? "min-h-16" : "min-h-12"}`} /><div className="mt-2 flex items-center justify-between"><input ref={inputRef} type="file" multiple accept=".pdf,application/pdf" className="hidden" onChange={(event: ChangeEvent<HTMLInputElement>) => void addFiles(event.target.files)} /><div className="flex items-center gap-2"><button type="button" onClick={() => inputRef.current?.click()} className="grid size-10 place-items-center rounded-full text-slate-600 hover:bg-slate-100" title="Upload PDF financial documents"><Plus size={24} /></button><GoalPlanningEntryButton disabled={sending} onClick={onSetGoal} /></div><button type="submit" disabled={!canSend} className={`grid size-10 place-items-center rounded-full transition ${canSend ? "bg-blue-600 text-white hover:bg-blue-700" : "bg-slate-200 text-slate-400"}`} title="Send message"><Send size={18} /></button></div></form>;
}

async function toPreview(file: File): Promise<AttachmentPreview> {
  const isImage = isImageFile(file);
  return { id: crypto.randomUUID(), name: file.name, extension: fileExtension(file), isImage, file, dataUrl: isImage ? await readImage(file) : undefined };
}

export default function AdvisorChat() {
  const { user } = useUser();
  const location = useLocation();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [localAttachments, setLocalAttachments] = useState<LocalAttachmentMap>({});
  const [draftConversationId, setDraftConversationId] = useState<number | null>(null);
  const [suggestedQuestions] = useState(selectSuggestedQuestions);
  const [goalPlanningPending, setGoalPlanningPending] = useState(false);
  const [pendingExchange, setPendingExchange] = useState<PendingExchange | null>(null);
  const [pendingGoalReview, setPendingGoalReview] = useState<GoalReviewCardData | null>(null);
  const [memoryUpdateCount, setMemoryUpdateCount] = useState(0);
  const activeRequestControllerRef = useRef<AbortController | null>(null);
  const memoryToastTimerRef = useRef<number | null>(null);
  const requestedGoalReview = useMemo(
    () => goalReviewRouteState(location.state),
    [location.state],
  );
  const initialGoalReviewRef = useRef(requestedGoalReview);
  const userName = user?.username?.trim()
    || user?.email.split("@")[0]
    || "there";
  const goalPlanningMode = goalPlanningPending || (
    getGoalPlanningUiState(active?.messages || []).startMessageId !== null
  );
  const goalReviewMode = pendingGoalReview !== null || (
    active?.messages.some(
      (message) => parseGoalReviewMessage(message.content) !== null,
    ) ?? false
  );
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
    rememberSuggestedQuestions(suggestedQuestions);
  }, [suggestedQuestions]);

  useEffect(
    () => () => {
      activeRequestControllerRef.current?.abort();
      if (memoryToastTimerRef.current !== null) {
        window.clearTimeout(memoryToastTimerRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    setConversations([]);
    setActive(null);
    setLocalAttachments({});
    setDraftConversationId(null);
    setError("");
    if (!user?.id) { setLoading(false); return; }
    setLoading(true);
    loadList()
      .then(async (items) => {
        if (!initialGoalReviewRef.current && items[0]) {
          setActive(await getConversation(items[0].conversation_id));
        }
      })
      .catch((caught) => setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load conversations.",
      ))
      .finally(() => setLoading(false));
  }, [loadList, user?.id]);

  useEffect(() => {
    if (
      loading
      || !requestedGoalReview
      || handledGoalReviewRequests.has(requestedGoalReview.requestId)
    ) {
      return;
    }
    handledGoalReviewRequests.add(requestedGoalReview.requestId);
    navigate(location.pathname, { replace: true, state: null });
    void startGoalReview(requestedGoalReview);
  }, [
    loading,
    location.pathname,
    navigate,
    requestedGoalReview,
  ]);

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
    try {
      setError("");
      await deleteConversation(id);
      const items = await loadList();
      setActive(
        items[0]
          ? await getConversation(items[0].conversation_id)
          : null,
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to delete conversation.",
      );
    }
  }

  function attachToLatestUserMessage(next: ConversationDetail, files: AttachmentPreview[]) {
    const userMessages = next.messages.filter((item) => item.role === "user");
    const latest = userMessages[userMessages.length - 1]; if (!latest || !files.length) return;
    setLocalAttachments((current) => ({ ...current, [latest.id]: files }));
  }

  function showMemoryUpdateToast(updateCount: number) {
    const visibleCount = Math.max(1, Math.trunc(updateCount));
    setMemoryUpdateCount(visibleCount);
    if (memoryToastTimerRef.current !== null) {
      window.clearTimeout(memoryToastTimerRef.current);
    }
    memoryToastTimerRef.current = window.setTimeout(() => {
      setMemoryUpdateCount(0);
      memoryToastTimerRef.current = null;
    }, 4_000);
  }

  function dismissMemoryUpdateToast() {
    setMemoryUpdateCount(0);
    if (memoryToastTimerRef.current !== null) {
      window.clearTimeout(memoryToastTimerRef.current);
      memoryToastTimerRef.current = null;
    }
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
    const requestController = new AbortController();
    activeRequestControllerRef.current?.abort();
    activeRequestControllerRef.current = requestController;
    setSending(true);
    setError("");
    setPendingExchange({
      conversationId: active?.conversation_id ?? null,
      userContent: message || "Extract financial information from the uploaded PDF.",
      files,
      assistantContent: "",
      thinking: true,
    });
    let conversationId = active?.conversation_id;
    try {
      const conversation = active || {
        ...(await createConversation()),
        messages: [],
      };
      conversationId = conversation.conversation_id;
      setPendingExchange((current) => current && ({
        ...current,
        conversationId: conversation.conversation_id,
      }));
      if (!active) {
        setDraftConversationId(conversation.conversation_id);
        setActive(conversation);
      }
      if (files.length) {
        const response = await sendAdvisorPdfMessage(
          message || "Extract financial information from the uploaded PDF.",
          conversation.conversation_id,
          files.map((item) => item.file),
          requestController.signal,
        );
        setPendingExchange((current) => current && ({
          ...current,
          assistantContent: response.answer,
          thinking: false,
        }));
        if (response.memory_updated) {
          showMemoryUpdateToast(response.memory_update_count);
        }
      } else {
        const response = await streamAdvisorMessage(
          message,
          conversation.conversation_id,
          (content) => setPendingExchange((current) => current && ({
            ...current,
            assistantContent: current.assistantContent + content,
            thinking: false,
          })),
          undefined,
          undefined,
          requestController.signal,
        );
        setPendingExchange((current) => current && ({
          ...current,
          assistantContent: response.answer,
          thinking: false,
        }));
        if (response.memory_updated) {
          showMemoryUpdateToast(response.memory_update_count);
        }
      }
      await refreshActiveConversation(conversation.conversation_id, files);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to send your message.",
      );
      if (conversationId !== undefined) {
        await refreshActiveConversation(conversationId, files).catch(() => undefined);
      }
    } finally {
      if (activeRequestControllerRef.current === requestController) {
        activeRequestControllerRef.current = null;
      }
      setPendingExchange(null);
      setSending(false);
    }
  }

  async function startGoalReview(request: GoalReviewRouteState) {
    const requestController = new AbortController();
    activeRequestControllerRef.current?.abort();
    activeRequestControllerRef.current = requestController;
    setSending(true);
    setError("");
    setActive(null);
    setDraftConversationId(null);
    setPendingGoalReview(request.goal);
    setPendingExchange({
      conversationId: null,
      userContent: "",
      files: [],
      assistantContent: "",
      thinking: true,
    });
    let conversationId: number | null = null;
    try {
      const created = await createConversation(
        `Goal review: ${request.goal.name}`.slice(0, 255),
      );
      conversationId = created.conversation_id;
      setActive({ ...created, messages: [] });
      setDraftConversationId(conversationId);
      setPendingExchange((current) => current && ({
        ...current,
        conversationId,
      }));
      const prompt = (
        "Please review this existing financial goal and suggest "
        + "practical, prioritised improvements."
      );
      const response = await streamAdvisorMessage(
        prompt,
        conversationId,
        (content) => setPendingExchange((current) => current && ({
          ...current,
          assistantContent: current.assistantContent + content,
          thinking: false,
        })),
        undefined,
        request.goal.goal_id,
        requestController.signal,
      );
      setPendingExchange((current) => current && ({
        ...current,
        assistantContent: response.answer,
        thinking: false,
      }));
      if (response.memory_updated) {
        showMemoryUpdateToast(response.memory_update_count);
      }
      await refreshActiveConversation(conversationId);
    } catch (caught) {
      if (conversationId !== null) {
        try {
          await refreshActiveConversation(conversationId);
        } catch {
          // Keep the original review error visible.
        }
      }
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to review this goal.",
      );
    } finally {
      if (activeRequestControllerRef.current === requestController) {
        activeRequestControllerRef.current = null;
      }
      setPendingGoalReview(null);
      setPendingExchange(null);
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
    setGoalPlanningPending(true);
    void appendGoalPlanningPrompt(GOAL_PLANNING_START_MESSAGE)
      .finally(() => setGoalPlanningPending(false));
  }

  function selectGoalCategory(categoryId: GoalCategoryId) {
    void appendGoalPlanningPrompt(goalCategoryPrompt(categoryId));
  }

  if (loading) {
    return <main className="p-10 text-slate-500">Loading conversations...</main>;
  }

  return (
    <main className="flex min-h-screen bg-slate-50">
      <MobileHistoryHandle open={historyOpen} onClick={() => setHistoryOpen((value) => !value)} />
      <button type="button" onClick={() => setHistoryOpen(false)} className={`fixed inset-0 z-40 bg-slate-950/40 transition-opacity duration-[650ms] lg:hidden ${historyOpen ? "opacity-100" : "pointer-events-none opacity-0"}`} aria-label="Close conversation history overlay" />
      <ConversationSidebar
        conversations={orderedConversations}
        activeId={active?.conversation_id}
        disabled={sending}
        mobile
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onNew={startConversation}
        onSelect={(id) => void selectConversation(id)}
        onDelete={(id) => void removeConversation(id)}
      />
      {historyOpen && (
        <ConversationSidebar
          conversations={orderedConversations}
          activeId={active?.conversation_id}
          disabled={sending}
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
            className="hidden size-11 shrink-0 place-items-center rounded-full bg-white text-slate-600 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-blue-100 lg:grid"
          >
            <PanelLeft size={22} aria-hidden="true" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="text-3xl font-bold tracking-tight">Advisor Chat</h1>
            <p className="mt-2 text-slate-500">
              Ask educational questions about personal finance.
            </p>
          </div>
        </div>
        {error && (
          <p className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <MessageList
          messages={active?.messages || []}
          attachments={localAttachments}
          pending={
            pendingExchange?.conversationId
              === (active?.conversation_id ?? null)
              ? pendingExchange
              : null
          }
          sending={sending}
          userName={userName}
          pendingGoalReview={pendingGoalReview}
          onSelectGoalCategory={selectGoalCategory}
        />
        <div className="mt-6">
          {!goalPlanningMode && !goalReviewMode && (
            <SuggestedQuestions
              disabled={sending}
              questions={suggestedQuestions}
              onSelect={(question) => void sendMessage(question, [])}
            />
          )}
          <ChatComposer sending={sending} onSubmit={sendMessage} onSetGoal={startGoalPlanning} />
        </div>
      </section>
      {memoryUpdateCount > 0 && (
        <MemoryUpdateToast
          count={memoryUpdateCount}
          onDismiss={dismissMemoryUpdateToast}
        />
      )}
    </main>
  );
}
