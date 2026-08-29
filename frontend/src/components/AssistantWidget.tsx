import { useEffect, useRef, useState } from "react";

import { type ChatMessage, useAssistant } from "../hooks/useAssistant";

const SUGGESTIONS = [
  "How do I scope an IAM policy to least privilege?",
  "What are S3 bucket security best practices?",
  "How can an SCP enforce required tags?",
];

/**
 * Floating AI assistant: a launcher pinned bottom-right that opens a chat panel.
 * It answers general AWS best-practice questions ONLY — the label says so, and the
 * architecture backs it up (the backend has no account access and no tools). Model
 * output is rendered as plain text, never HTML.
 */
export function AssistantWidget() {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const { messages, loading, error, send } = useAssistant();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view as the thread grows or a reply streams in.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, loading]);

  const submit = () => {
    send(draft);
    setDraft("");
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full border border-line bg-surface-panel px-4 py-3 text-sm font-medium text-ink shadow-lg shadow-black/10 transition hover:border-line-strong"
      >
        <SparkGlyph />
        {open ? "Close assistant" : "Ask the assistant"}
      </button>

      {open && (
        <section
          aria-label="AWS best-practices assistant"
          className="fixed bottom-24 right-6 z-40 flex h-[min(32rem,70vh)] w-[min(24rem,calc(100vw-3rem))] flex-col overflow-hidden rounded-2xl border border-line bg-surface-panel shadow-2xl shadow-black/20"
        >
          <header className="border-b border-line px-4 py-3">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="grid h-7 w-7 place-items-center rounded-lg bg-accent-wash text-accent"
              >
                <SparkGlyph size={15} />
              </span>
              <h2 className="text-sm font-semibold text-ink">Best-practices assistant</h2>
            </div>
            <p className="mt-1 font-mono text-[11px] text-ink-faint">
              general AWS guidance · no account access
            </p>
          </header>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 && !loading ? (
              <EmptyState onPick={send} />
            ) : (
              messages.map((m, i) => <Bubble key={i} message={m} />)
            )}
            {loading && <Thinking />}
            {error && (
              <p role="alert" className="px-1 text-xs text-status-error">
                {error}
              </p>
            )}
          </div>

          <form
            className="border-t border-line p-3"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <div className="flex items-end gap-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  // Enter sends; Shift+Enter inserts a newline.
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                rows={1}
                maxLength={4000}
                placeholder="Ask about AWS security best practices…"
                aria-label="Your question"
                className="max-h-28 min-h-[2.5rem] flex-1 resize-none rounded-lg border border-line bg-surface-base px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-line-strong"
              />
              <button
                type="submit"
                disabled={loading || draft.trim().length === 0}
                aria-label="Send"
                className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-accent text-surface-panel transition disabled:cursor-not-allowed disabled:opacity-40"
              >
                <SendGlyph />
              </button>
            </div>
          </form>
        </section>
      )}
    </>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          isUser
            ? "max-w-[85%] rounded-2xl rounded-br-sm bg-accent-wash px-3 py-2 text-sm text-ink"
            : "max-w-[85%] rounded-2xl rounded-bl-sm border border-line bg-surface-base px-3 py-2 text-sm text-ink"
        }
      >
        {/* Model output is untrusted → rendered as plain text with whitespace
            preserved, NEVER dangerouslySetInnerHTML, so it can't inject markup. */}
        <p className="whitespace-pre-wrap break-words">{message.content}</p>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-dim">
        Ask about AWS security &amp; compliance best practices. I give general guidance and{" "}
        <span className="text-ink">can&apos;t see your account</span> — no findings, credentials,
        or actions.
      </p>
      <div className="space-y-2">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="w-full rounded-lg border border-line bg-surface-base px-3 py-2 text-left text-xs text-ink-dim transition hover:border-line-strong hover:text-ink"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function Thinking() {
  return (
    <div className="flex justify-start">
      <div
        aria-label="Assistant is thinking"
        className="flex items-center gap-1 rounded-2xl rounded-bl-sm border border-line bg-surface-base px-3 py-2.5"
      >
        <Dot />
        <Dot delay="150ms" />
        <Dot delay="300ms" />
      </div>
    </div>
  );
}

function Dot({ delay = "0ms" }: { delay?: string }) {
  return (
    <span
      aria-hidden
      className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-faint"
      style={{ animationDelay: delay }}
    />
  );
}

function SparkGlyph({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 3l1.7 5.1a3 3 0 0 0 1.9 1.9L21 12l-5.4 1.8a3 3 0 0 0-1.9 1.9L12 21l-1.7-5.3a3 3 0 0 0-1.9-1.9L3 12l5.4-1.1A3 3 0 0 0 10.3 8L12 3Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SendGlyph() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M22 2 11 13"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M22 2 15 22l-4-9-9-4 20-7Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
