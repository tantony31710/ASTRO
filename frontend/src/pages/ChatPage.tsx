import { useState, useRef, useEffect } from "react";
import { sendChat } from "../api/client";

interface Message {
  role: "user" | "jarvis";
  text: string;
  tool?: string | null;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "jarvis", text: "Vault online. Ask me to check disk space, clean cache, list weights, or anything else." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    setError(null);
    try {
      const res = await sendChat(text);
      setMessages((m) => [...m, { role: "jarvis", text: res.reply, tool: res.matched_tool }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the vault API.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">04 · Assistant</div>
          <h1 className="page-title">Chat</h1>
          <p className="page-desc">
            Routed through the tool registry first — unmatched requests fall back to whichever LLM is configured.
          </p>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="panel" style={{ marginBottom: 16 }}>
        <div
          ref={scrollRef}
          style={{ maxHeight: 420, minHeight: 240, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}
        >
          {messages.map((m, i) => (
            <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "80%" }}>
              <div
                style={{
                  background: m.role === "user" ? "var(--accent-soft)" : "var(--panel-alt)",
                  border: `1px solid ${m.role === "user" ? "var(--accent-dim)" : "var(--border)"}`,
                  borderRadius: "var(--radius-sm)",
                  padding: "8px 12px",
                  fontSize: 13.5,
                }}
              >
                {m.text}
              </div>
              {m.tool && <div className="hint" style={{ marginTop: 4 }}>tool: {m.tool}</div>}
            </div>
          ))}
          {sending && <div className="hint">thinking…</div>}
        </div>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="e.g. check disk space"
          style={{
            flex: 1,
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "10px 14px",
            color: "var(--text)",
            fontSize: 13.5,
            fontFamily: "var(--font-body)",
          }}
        />
        <button className="btn" onClick={handleSend} disabled={sending || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
