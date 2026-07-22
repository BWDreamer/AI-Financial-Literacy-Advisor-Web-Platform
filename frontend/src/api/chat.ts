import { ApiError, apiRequest, apiResponse } from "./client";

export type ChatMessage = { id: number; role: "user" | "assistant"; content: string; created_at: string };
export type Conversation = { conversation_id: number; title: string; created_at: string; updated_at: string };
export type ConversationDetail = Conversation & { messages: ChatMessage[] };
export type ImportedFinancialRecord = {
  record_type: string;
  name: string;
  amount: number;
  asset_type?: string | null;
  flow_type?: string | null;
  date?: string | null;
};
export type PdfAdvisorResponse = {
  answer: string;
  model: string;
  low_confidence: boolean;
  extracted_text_characters: number;
  imported_records: ImportedFinancialRecord[];
  fallback_reason?: string | null;
};
export type AdvisorStreamResponse = { answer: string; model: string };

type AdvisorStreamEvent =
  | { type: "delta"; content: string }
  | { type: "done"; answer: string; model: string }
  | { type: "error"; message: string; status: number };

function parseAdvisorStreamEvent(line: string): AdvisorStreamEvent {
  let parsedPayload: unknown;
  try {
    parsedPayload = JSON.parse(line);
  } catch {
    throw new ApiError("The server returned an invalid AI response.", 502);
  }
  if (
    !parsedPayload
    || typeof parsedPayload !== "object"
    || Array.isArray(parsedPayload)
  ) {
    throw new ApiError("The server returned an invalid AI response.", 502);
  }
  const payload = parsedPayload as Record<string, unknown>;
  if (payload.type === "delta" && typeof payload.content === "string") {
    return { type: "delta", content: payload.content };
  }
  if (
    payload.type === "done"
    && typeof payload.answer === "string"
    && typeof payload.model === "string"
  ) {
    return { type: "done", answer: payload.answer, model: payload.model };
  }
  if (
    payload.type === "error"
    && typeof payload.message === "string"
    && typeof payload.status === "number"
  ) {
    return { type: "error", message: payload.message, status: payload.status };
  }
  throw new ApiError("The server returned an invalid AI response.", 502);
}

export const getConversations = () => apiRequest<Conversation[]>("/chat/conversations", { authenticated: true });
export const getConversation = (id: number) => apiRequest<ConversationDetail>(`/chat/conversations/${id}`, { authenticated: true });
export const createConversation = (title?: string) => apiRequest<Conversation>("/chat/conversations", { method: "POST", authenticated: true, body: JSON.stringify({ title }) });
export const addConversationMessage = (id: number, role: ChatMessage["role"], content: string) => apiRequest<ChatMessage>(`/chat/conversations/${id}/messages`, { method: "POST", authenticated: true, body: JSON.stringify({ role, content }) });
export const deleteConversation = (id: number) => apiRequest<void>(`/chat/conversations/${id}`, { method: "DELETE", authenticated: true });
export const sendAdvisorMessage = (message: string, conversationId: number, ruleId?: number) => apiRequest<{ answer: string; model: string }>("/ai/chat", {
  method: "POST", authenticated: true,
  body: JSON.stringify({ message, conversation_id: conversationId, rule_id: ruleId }),
});

export async function streamAdvisorMessage(
  message: string,
  conversationId: number,
  onDelta: (content: string) => void,
  ruleId?: number,
): Promise<AdvisorStreamResponse> {
  const response = await apiResponse("/ai/chat/stream", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      rule_id: ruleId,
    }),
  });
  if (!response.body) {
    throw new ApiError("The browser could not read the AI response stream.", 502);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let bufferedText = "";
  let completedResponse: AdvisorStreamResponse | null = null;

  function processLine(rawLine: string) {
    const line = rawLine.trim();
    if (!line) return;
    const event = parseAdvisorStreamEvent(line);
    if (event.type === "delta") {
      onDelta(event.content);
    } else if (event.type === "done") {
      completedResponse = {
        answer: event.answer,
        model: event.model,
      };
    } else {
      throw new ApiError(event.message, event.status);
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      bufferedText += decoder.decode(value, { stream: !done });
      const lines = bufferedText.split("\n");
      bufferedText = lines.pop() || "";
      lines.forEach(processLine);
      if (done) break;
    }
    processLine(bufferedText);
  } finally {
    reader.releaseLock();
  }

  if (!completedResponse) {
    throw new ApiError("The AI response stream ended unexpectedly.", 502);
  }
  return completedResponse;
}

export function sendAdvisorPdfMessage(message: string, conversationId: number, files: File[]) {
  const form = new FormData();
  form.set("message", message);
  form.set("conversation_id", String(conversationId));
  files.forEach((file) => form.append("files", file));
  return apiRequest<PdfAdvisorResponse>("/ai/chat/pdf", {
    method: "POST",
    authenticated: true,
    body: form,
  });
}
