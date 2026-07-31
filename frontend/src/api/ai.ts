import { apiRequest } from "./client";

export type AdvisorChatResponse = {
  answer: string;
  model: string;
  memory_updated: boolean;
  memory_update_count: number;
};

export function sendAdvisorMessage(message: string) {
  return apiRequest<AdvisorChatResponse>("/ai/chat", {
    method: "POST",
    authenticated: true,
    body: JSON.stringify({ message }),
  });
}
