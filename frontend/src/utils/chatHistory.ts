const CHAT_HISTORY_KEY = "financeai_chat_history";

export type ChatRole = "user" | "assistant";
export type ChatMessage = { id: string; role: ChatRole; content: string };
export type ChatConversation = { id: string; title: string; updatedAt: string; messages: ChatMessage[] };

export function createConversation(): ChatConversation {
  return { id: crypto.randomUUID(), title: "New conversation", updatedAt: new Date().toISOString(), messages: [] };
}

export function loadConversations() {
  // TODO: Replace localStorage with a backend conversation history API when one is available.
  const stored = localStorage.getItem(CHAT_HISTORY_KEY);
  return stored ? JSON.parse(stored) as ChatConversation[] : [];
}

export function saveConversations(conversations: ChatConversation[]) {
  // TODO: Replace localStorage with a backend conversation history API when one is available.
  localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(conversations));
}

export function makeMessage(role: ChatRole, content: string): ChatMessage {
  return { id: crypto.randomUUID(), role, content };
}

export function conversationTitle(message: string) {
  return message.length > 42 ? `${message.slice(0, 42)}...` : message || "New conversation";
}
