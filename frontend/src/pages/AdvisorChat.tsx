import { FormEvent, useMemo, useState } from "react";
import { Bot, MessageSquarePlus, Send } from "lucide-react";
import { sendAdvisorMessage } from "../api/ai";
import { ChatConversation, conversationTitle, createConversation, loadConversations, makeMessage, saveConversations } from "../utils/chatHistory";

function useChatHistory() {
  const [conversations, setConversations] = useState<ChatConversation[]>(() => {
    const stored = loadConversations();
    return stored.length ? stored : [createConversation()];
  });
  const [activeId, setActiveId] = useState(conversations[0].id);
  function persist(next: ChatConversation[]) { setConversations(next); saveConversations(next); }
  function startConversation() { const next = [createConversation(), ...conversations]; persist(next); setActiveId(next[0].id); }
  return { conversations, activeId, setActiveId, persist, startConversation };
}

function HistoryPanel({ items, activeId, onSelect, onNew }: { items: ChatConversation[]; activeId: string; onSelect: (id: string) => void; onNew: () => void }) {
  return <aside className="w-80 shrink-0 border-l border-slate-200 bg-white p-5"><button type="button" onClick={onNew} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700"><MessageSquarePlus size={18} />New Chat</button>
    <h2 className="mt-6 text-xs font-bold uppercase tracking-[0.16em] text-slate-400">Conversation History</h2><div className="mt-3 space-y-2">{items.map((item) => <button key={item.id} type="button" onClick={() => onSelect(item.id)} className={`w-full rounded-xl border px-3 py-3 text-left transition ${item.id === activeId ? "border-blue-300 bg-blue-50 text-blue-900" : "border-slate-200 hover:bg-slate-50"}`}>
      <span className="block truncate text-sm font-semibold">{item.title}</span><span className="mt-1 block text-xs text-slate-500">{new Date(item.updatedAt).toLocaleString()}</span></button>)}</div></aside>;
}

function MessageBubble({ role, content }: { role: "user" | "assistant"; content: string }) {
  const isUser = role === "user";
  return <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}><div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${isUser ? "bg-blue-600 text-white" : "border border-slate-200 bg-white text-slate-700"}`}>{content}</div></div>;
}

function EmptyChat() {
  return <div className="grid h-full place-items-center text-center"><div><span className="mx-auto grid size-14 place-items-center rounded-2xl bg-blue-50 text-blue-600"><Bot size={28} /></span><h2 className="mt-4 text-2xl font-bold text-slate-900">Advisor Chat</h2><p className="mt-2 max-w-md text-sm text-slate-500">Ask a financial literacy question and FinanceAI will reply using the real AI Advisor backend.</p></div></div>;
}

function updateConversation(conversations: ChatConversation[], id: string, updater: (item: ChatConversation) => ChatConversation) {
  return conversations.map((item) => item.id === id ? updater(item) : item);
}

export default function AdvisorChat() {
  const history = useChatHistory(); const [input, setInput] = useState(""); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  const active = useMemo(() => history.conversations.find((item) => item.id === history.activeId) || history.conversations[0], [history]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const message = input.trim(); if (!message || loading) return;
    setInput(""); setError(""); setLoading(true); const userMessage = makeMessage("user", message);
    history.persist(updateConversation(history.conversations, active.id, (item) => ({ ...item, title: item.messages.length ? item.title : conversationTitle(message), updatedAt: new Date().toISOString(), messages: [...item.messages, userMessage] })));
    try {
      const reply = await sendAdvisorMessage(message); const assistantMessage = makeMessage("assistant", reply.answer);
      history.persist(updateConversation(loadConversations(), active.id, (item) => ({ ...item, updatedAt: new Date().toISOString(), messages: [...item.messages, assistantMessage] })));
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to send your message."); }
    finally { setLoading(false); }
  }
  return <div className="flex h-screen min-h-0 bg-slate-50"><section className="flex min-w-0 flex-1 flex-col"><header className="border-b border-slate-200 bg-white px-8 py-5"><h1 className="text-2xl font-bold tracking-tight text-slate-900">Advisor Chat</h1><p className="mt-1 text-sm text-slate-500">Chat with your FinanceAI advisor.</p></header>
    <div className="min-h-0 flex-1 overflow-y-auto p-8">{active.messages.length ? <div className="space-y-4">{active.messages.map((message) => <MessageBubble key={message.id} role={message.role} content={message.content} />)}{loading && <MessageBubble role="assistant" content="Thinking..." />}</div> : <EmptyChat />}</div>
    <form onSubmit={submit} className="border-t border-slate-200 bg-white p-5"><div className="flex gap-3"><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Type your message..." className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" /><button disabled={loading || !input.trim()} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"><Send size={18} />Send</button></div>{error && <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}</form></section>
    <HistoryPanel items={history.conversations} activeId={history.activeId} onSelect={history.setActiveId} onNew={history.startConversation} /></div>;
}
