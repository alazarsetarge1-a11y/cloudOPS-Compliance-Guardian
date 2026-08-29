import { useCallback, useState } from "react";

import { apiPost, safeErrorMessage } from "../lib/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface AssistantReply {
  answer: string;
}

// Mirrors the backend cap (schemas.AssistantAsk.history max_length=12): only the
// most recent turns are sent as context, so every request stays bounded no matter
// how long the conversation runs.
const MAX_HISTORY = 12;

/**
 * Chat state for the best-practices assistant. Owns the message list and one
 * `send` action; the component stays presentational. The user's message is shown
 * optimistically, and prior turns (bounded) ride along as context.
 */
export function useAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (raw: string) => {
      const question = raw.trim();
      if (!question || loading) return;

      // Snapshot the prior turns for context BEFORE appending this one, and bound
      // them to the backend's cap.
      const history = messages.slice(-MAX_HISTORY);
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: question }]);
      setLoading(true);
      try {
        const reply = await apiPost<AssistantReply>("/assistant/ask", { question, history });
        setMessages((prev) => [...prev, { role: "assistant", content: reply.answer }]);
      } catch (e) {
        // Map by status, never echo the raw backend detail (same rule as the
        // dashboard): a 503 here means "assistant unavailable", not a scary trace.
        setError(safeErrorMessage(e));
      } finally {
        setLoading(false);
      }
    },
    [messages, loading],
  );

  return { messages, loading, error, send };
}
