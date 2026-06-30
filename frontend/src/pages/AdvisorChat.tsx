import { FormEvent, useCallback, useEffect, useState } from "react";
import { Conversation, ConversationDetail, createConversation, deleteConversation, getConversation, getConversations, sendAdvisorMessage } from "../api/chat";

export default function AdvisorChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [active, setActive] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const loadList = useCallback(async () => {
    const items = await getConversations();
    setConversations(items);
    return items;
  }, []);

  useEffect(() => {
    loadList().then(async (items) => {
      if (items[0]) setActive(await getConversation(items[0].conversation_id));
    }).catch((caught) => setError(caught instanceof Error ? caught.message : "Unable to load conversations."))
      .finally(() => setLoading(false));
  }, [loadList]);

  async function selectConversation(id: number) {
    setError("");
    try { setActive(await getConversation(id)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load this conversation."); }
  }

  async function startConversation() {
    const created = await createConversation();
    await loadList();
    setActive({ ...created, messages: [] });
  }

  async function removeConversation(id: number) {
    await deleteConversation(id);
    const items = await loadList();
    setActive(items[0] ? await getConversation(items[0].conversation_id) : null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const message = String(new FormData(form).get("message")).trim();
    if (!message) return;
    setSending(true); setError("");
    try {
      let conversation = active;
      if (!conversation) {
        const created = await createConversation();
        conversation = { ...created, messages: [] };
      }
      await sendAdvisorMessage(message, conversation.conversation_id);
      form.reset();
      setActive(await getConversation(conversation.conversation_id));
      await loadList();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to send your message.");
    } finally { setSending(false); }
  }

  if (loading) return <main className="p-10 text-slate-500">Loading conversations...</main>;

  return <main className="flex min-h-screen bg-slate-50">
    <aside className="w-64 border-r border-slate-200 bg-white p-4"><button type="button" onClick={() => void startConversation()} className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white">New Conversation</button><div className="mt-4 space-y-2">{conversations.length === 0 && <p className="p-3 text-sm text-slate-500">No saved conversations.</p>}{conversations.map((item) => <div key={item.conversation_id} className={`rounded-xl p-3 ${active?.conversation_id === item.conversation_id ? "bg-blue-50" : "hover:bg-slate-50"}`}><button type="button" className="w-full truncate text-left text-sm font-medium" onClick={() => void selectConversation(item.conversation_id)}>{item.title}</button><button type="button" className="mt-2 text-xs text-red-500" onClick={() => void removeConversation(item.conversation_id)}>Delete</button></div>)}</div></aside>
    <section className="flex min-w-0 flex-1 flex-col p-8"><div><h1 className="text-3xl font-bold tracking-tight">Advisor Chat</h1><p className="mt-2 text-slate-500">Ask educational questions about personal finance.</p></div>{error && <p className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}<div className="mt-6 flex-1 space-y-4">{!active?.messages.length && <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500">Start a conversation with your advisor.</p>}{active?.messages.map((message) => <article key={message.id} className={`max-w-2xl rounded-2xl p-4 ${message.role === "user" ? "ml-auto bg-blue-600 text-white" : "bg-white shadow-sm"}`}><p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p></article>)}</div><form onSubmit={submit} className="mt-6 flex gap-3"><input name="message" required placeholder="Ask a financial question..." className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" /><button disabled={sending} className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white disabled:opacity-60">{sending ? "Sending..." : "Send"}</button></form></section>
  </main>;
}
