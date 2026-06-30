import { apiRequest } from "./client";

export type ChatMessage = { id: number; role: "user" | "assistant"; content: string; created_at: string };
export type Conversation = { conversation_id: number; title: string; created_at: string; updated_at: string };
export type ConversationDetail = Conversation & { messages: ChatMessage[] };

export const getConversations = () => apiRequest<Conversation[]>("/chat/conversations", { authenticated: true });
export const getConversation = (id: number) => apiRequest<ConversationDetail>(`/chat/conversations/${id}`, { authenticated: true });
export const createConversation = (title?: string) => apiRequest<Conversation>("/chat/conversations", { method: "POST", authenticated: true, body: JSON.stringify({ title }) });
export const addConversationMessage = (id: number, role: ChatMessage["role"], content: string) => apiRequest<ChatMessage>(`/chat/conversations/${id}/messages`, { method: "POST", authenticated: true, body: JSON.stringify({ role, content }) });
export const deleteConversation = (id: number) => apiRequest<void>(`/chat/conversations/${id}`, { method: "DELETE", authenticated: true });
export const sendAdvisorMessage = (message: string, conversationId: number, ruleId?: number) => apiRequest<{ answer: string; model: string }>("/ai/chat", {
  method: "POST", authenticated: true,
  body: JSON.stringify({ message, conversation_id: conversationId, rule_id: ruleId }),
});
