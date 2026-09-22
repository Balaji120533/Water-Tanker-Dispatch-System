import { useState, useRef, useEffect } from "react";

const API_BASE = "http://localhost:8000";

const GREETING = {
  role: "assistant",
  kind: "text",
  text: "Hello! Tell me about your area's water situation — for example, \"the tank in Manali is almost empty\" — and I'll check whether you're due a delivery.",
};

export default function App() {
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setMessages((m) => [...m, { role: "user", kind: "text", text }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/volunteer/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();

      if (!res.ok) {
        setMessages((m) => [
          ...m,
          { role: "assistant", kind: "text", text: data.detail || "Something went wrong. Please try again." },
        ]);
      } else {
        setMessages((m) => [...m, { role: "assistant", kind: "decision", data }]);
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", kind: "text", text: "Could not reach the dispatch system. Please try again shortly." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">
      <header className="bg-white border-b border-slate-200 px-4 py-3">
        <h1 className="text-base font-semibold text-slate-900">Water help</h1>
        <p className="text-xs text-slate-500">Report your area's water condition</p>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((m, i) =>
          m.kind === "decision" ? (
            <DecisionBubble key={i} data={m.data} />
          ) : (
            <TextBubble key={i} role={m.role} text={m.text} />
          )
        )}
        {loading && <TextBubble role="assistant" text="Checking..." muted />}
        <div ref={bottomRef} />
      </main>

      <form onSubmit={send} className="bg-white border-t border-slate-200 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 border border-slate-300 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  );
}

function TextBubble({ role, text, muted }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : `bg-white text-slate-700 rounded-bl-sm border border-slate-200 ${muted ? "italic text-slate-400" : ""}`
        }`}
      >
        {text}
      </div>
    </div>
  );
}

function DecisionBubble({ data }) {
  const badge = !data.entitled
    ? { cls: "bg-slate-100 text-slate-600", label: "Not currently entitled" }
    : data.high_priority
    ? { cls: "bg-red-100 text-red-700", label: "High priority" }
    : { cls: "bg-green-100 text-green-700", label: "Entitled" };

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3">
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badge.cls}`}>
          {badge.label}
        </span>

        <p className="text-sm text-slate-700 mt-2">{data.explanation}</p>

        {data.entitled && (
          <p className="text-sm text-slate-500 mt-2">
            {data.estimated_slot
              ? `Scheduled today: tanker ${data.estimated_slot.tanker_id}, slot ${data.estimated_slot.slot}.`
              : data.estimated_slot_note}
          </p>
        )}

        <details className="mt-2">
          <summary className="text-xs text-slate-400 cursor-pointer">
            What I understood / full derivation
          </summary>
          <div className="mt-2 text-xs text-slate-500">
            <p className="mb-1">
              Area: <strong>{data.understood.zone_name}</strong> · Tank:{" "}
              <strong>{data.understood.tank_level_percent}%</strong>
              {data.understood.days_since_delivery != null && (
                <> · {data.understood.days_since_delivery} days since delivery</>
              )}
            </p>
            {data.proof_trace && (
              <pre className="whitespace-pre-wrap bg-slate-50 rounded p-2 mt-1">{data.proof_trace}</pre>
            )}
          </div>
        </details>
      </div>
    </div>
  );
}
