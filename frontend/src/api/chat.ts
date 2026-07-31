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
export type AdvisorResponse = {
  answer: string;
  model: string;
  memory_updated: boolean;
  memory_update_count: number;
};
export type PdfAdvisorResponse = AdvisorResponse & {
  low_confidence: boolean;
  extracted_text_characters: number;
  imported_records: ImportedFinancialRecord[];
  fallback_reason?: string | null;
};
export type AdvisorStreamResponse = AdvisorResponse;

type AdvisorStreamEvent =
  | { type: "delta"; content: string }
  | ({ type: "done" } & AdvisorResponse)
  | { type: "error"; message: string; status: number };

const STREAM_RENDER_INTERVAL_MS = 35;
const STREAM_CHARACTERS_PER_TICK = 2;
const STREAM_RENDER_MAX_DURATION_MS = 20_000;

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
    const memoryUpdateCount = (
      typeof payload.memory_update_count === "number"
      && Number.isInteger(payload.memory_update_count)
      && payload.memory_update_count >= 0
    )
      ? payload.memory_update_count
      : 0;
    return {
      type: "done",
      answer: payload.answer,
      model: payload.model,
      memory_updated: payload.memory_updated === true,
      memory_update_count: memoryUpdateCount,
    };
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

function createIncrementalTextRenderer(
  onDelta: (content: string) => void,
) {
  // Keep network consumption fast while revealing a small, readable increment.
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  const pendingCharacters: string[] = [];
  const drainResolvers: Array<() => void> = [];
  let timerId: number | null = null;
  let renderStartedAt: number | null = null;
  let nextCharacterIndex = 0;

  function resolveDrainsWhenIdle() {
    if (
      timerId !== null
      || nextCharacterIndex < pendingCharacters.length
    ) {
      return;
    }
    pendingCharacters.splice(0);
    nextCharacterIndex = 0;
    drainResolvers.splice(0).forEach((resolve) => resolve());
  }

  function shouldFinishImmediately() {
    return (
      reduceMotion
      || document.visibilityState !== "visible"
      || (
        renderStartedAt !== null
        && Date.now() - renderStartedAt >= STREAM_RENDER_MAX_DURATION_MS
      )
    );
  }

  function flushPendingText() {
    if (timerId !== null) {
      window.clearTimeout(timerId);
      timerId = null;
    }
    if (nextCharacterIndex < pendingCharacters.length) {
      onDelta(pendingCharacters.slice(nextCharacterIndex).join(""));
      nextCharacterIndex = pendingCharacters.length;
    }
    resolveDrainsWhenIdle();
  }

  function renderNextIncrement() {
    timerId = null;
    if (nextCharacterIndex >= pendingCharacters.length) {
      resolveDrainsWhenIdle();
      return;
    }
    if (shouldFinishImmediately()) {
      flushPendingText();
      return;
    }
    const incrementSize = Math.min(
      STREAM_CHARACTERS_PER_TICK,
      pendingCharacters.length - nextCharacterIndex,
    );
    onDelta(
      pendingCharacters
        .slice(nextCharacterIndex, nextCharacterIndex + incrementSize)
        .join(""),
    );
    nextCharacterIndex += incrementSize;
    scheduleNextIncrement();
  }

  function scheduleNextIncrement() {
    if (
      timerId !== null
      || nextCharacterIndex >= pendingCharacters.length
    ) {
      resolveDrainsWhenIdle();
      return;
    }
    timerId = window.setTimeout(
      renderNextIncrement,
      STREAM_RENDER_INTERVAL_MS,
    );
  }

  return {
    enqueue(content: string) {
      if (!content) return;
      renderStartedAt ??= Date.now();
      if (shouldFinishImmediately()) {
        flushPendingText();
        onDelta(content);
        return;
      }
      pendingCharacters.push(...Array.from(content));
      scheduleNextIncrement();
    },
    drain(): Promise<void> {
      if (shouldFinishImmediately()) {
        flushPendingText();
      }
      if (
        timerId === null
        && nextCharacterIndex >= pendingCharacters.length
      ) {
        return Promise.resolve();
      }
      return new Promise((resolve) => {
        drainResolvers.push(resolve);
      });
    },
    cancel() {
      if (timerId !== null) {
        window.clearTimeout(timerId);
        timerId = null;
      }
      pendingCharacters.splice(0);
      nextCharacterIndex = 0;
      resolveDrainsWhenIdle();
    },
  };
}

export const getConversations = () => apiRequest<Conversation[]>("/chat/conversations", { authenticated: true });
export const getConversation = (id: number) => apiRequest<ConversationDetail>(`/chat/conversations/${id}`, { authenticated: true });
export const createConversation = (title?: string) => apiRequest<Conversation>("/chat/conversations", { method: "POST", authenticated: true, body: JSON.stringify({ title }) });
export const addConversationMessage = (id: number, role: ChatMessage["role"], content: string) => apiRequest<ChatMessage>(`/chat/conversations/${id}/messages`, { method: "POST", authenticated: true, body: JSON.stringify({ role, content }) });
export const deleteConversation = (id: number) => apiRequest<void>(`/chat/conversations/${id}`, { method: "DELETE", authenticated: true });
export const sendAdvisorMessage = (
  message: string,
  conversationId: number,
  ruleId?: number,
  goalId?: number,
) => apiRequest<AdvisorResponse>("/ai/chat", {
  method: "POST", authenticated: true,
  body: JSON.stringify({
    message,
    conversation_id: conversationId,
    rule_id: ruleId,
    goal_id: goalId,
  }),
});

export async function streamAdvisorMessage(
  message: string,
  conversationId: number,
  onDelta: (content: string) => void,
  ruleId?: number,
  goalId?: number,
  signal?: AbortSignal,
): Promise<AdvisorStreamResponse> {
  const response = await apiResponse("/ai/chat/stream", {
    method: "POST",
    authenticated: true,
    signal,
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      rule_id: ruleId,
      goal_id: goalId,
    }),
  });
  if (!response.body) {
    throw new ApiError("The browser could not read the AI response stream.", 502);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const incrementalRenderer = createIncrementalTextRenderer(onDelta);
  let bufferedText = "";
  let completedResponse: AdvisorStreamResponse | null = null;

  function processLine(rawLine: string) {
    const line = rawLine.trim();
    if (!line) return;
    const event = parseAdvisorStreamEvent(line);
    if (event.type === "delta") {
      incrementalRenderer.enqueue(event.content);
    } else if (event.type === "done") {
      completedResponse = {
        answer: event.answer,
        model: event.model,
        memory_updated: event.memory_updated,
        memory_update_count: event.memory_update_count,
      };
    } else {
      throw new ApiError(event.message, event.status);
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      bufferedText += decoder.decode(value, { stream: !done });
      const lines = bufferedText.split(/\r?\n/);
      bufferedText = lines.pop() || "";
      lines.forEach(processLine);
      if (done) break;
    }
    processLine(bufferedText);
    if (!completedResponse) {
      throw new ApiError("The AI response stream ended unexpectedly.", 502);
    }
    await incrementalRenderer.drain();
    return completedResponse;
  } catch (error) {
    incrementalRenderer.cancel();
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally {
    reader.releaseLock();
  }
}

export function sendAdvisorPdfMessage(
  message: string,
  conversationId: number,
  files: File[],
  signal?: AbortSignal,
) {
  const form = new FormData();
  form.set("message", message);
  form.set("conversation_id", String(conversationId));
  files.forEach((file) => form.append("files", file));
  return apiRequest<PdfAdvisorResponse>("/ai/chat/pdf", {
    method: "POST",
    authenticated: true,
    signal,
    body: form,
  });
}
