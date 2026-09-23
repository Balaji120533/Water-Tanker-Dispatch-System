import { useState, useRef, useEffect } from "react";
import StatusCard from "./StatusCard";

const API_BASE = "http://localhost:8000";

const GREETING =
  "Hello! Tell me about your area's water situation — for example, “the tank in Manali is almost empty” — and I'll check whether you're due a delivery.";

// Shown while the conversation is still gathering facts, so a first-time
// user isn't staring at an empty box wondering what to type.
const STARTERS = [
  "The tank in Vadapalani is almost empty",
  "No water in Anna Nagar for 4 days",
  "Ward 124 tank is getting low",
];

export default function App() {
  const [messages, setMessages] = useState([{ role: "assistant", text: GREETING }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [stage, setStage] = useState("collecting");
  const [status, setStatus] = useState(null);
  const bottomRef = useRef(null);
  const askedReceiptRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, status]);

  // Poll the session once a report is in, so the card tracks the delivery
  // and the receipt question appears as soon as the driver marks it done.
  useEffect(() => {
    if (!sessionId || stage === "collecting" || stage === "confirming") return;
    let cancelled = false;

    const tick = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/volunteer/session/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;

        setStatus(data.status);
        setStage(data.stage);

        // The backend asks for receipt confirmation once the driver marks
        // the delivery complete; surface that question in the chat once.
        if (data.stage === "awaiting_receipt" && !askedReceiptRef.current) {
          askedReceiptRef.current = true;
          setMessages((m) => [...m, { role: "assistant", text: data.status.question }]);
        }
      } catch {
        // Transient failure -- keep the last known status rather than
        // blanking the card mid-delivery.
      }
    };

    tick();
    const id = setInterval(tick, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [sessionId, stage]);

  const send = async (textOverride) => {
    const text = (textOverride ?? input).trim();
    if (!text || loading) return;

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/volunteer/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      const data = await res.json();

      if (!res.ok) {
        setMessages((m) => [
          ...m,
          { role: "assistant", text: data.detail || "Something went wrong. Please try again." },
        ]);
      } else {
        setSessionId(data.session_id);
        setStage(data.stage);
        setMessages((m) => [
          ...m,
          { role: "assistant", text: data.reply, decision: data.decision, facts: data.facts },
        ]);
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "Could not reach the dispatch system. Please try again shortly." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    send();
  };

  const awaitingYesNo = stage === "confirming" || stage === "awaiting_receipt";
  const showStarters = messages.length === 1 && !loading;

  return (
    <div className="h-screen flex flex-col bg-slate-100">
      <header className="bg-white border-b border-slate-200 px-4 py-3">
        <h1 className="text-base font-semibold text-slate-900">Water help</h1>
        <p className="text-xs text-slate-500">Report your area's water condition</p>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} text={m.text} decision={m.decision} facts={m.facts} />
        ))}

        {status && <StatusCard status={status} />}

        {loading && <Bubble role="assistant" text="Checking…" muted />}

        {showStarters && (
          <div className="pt-2 space-y-2">
            <p className="text-xs text-slate-400 px-1">Or tap an example:</p>
            {STARTERS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="block w-full text-left text-sm bg-white border border-slate-200 rounded-xl px-3 py-2 text-slate-600 hover:border-blue-400"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      <form onSubmit={onSubmit} className="bg-white border-t border-slate-200 p-3">
        {awaitingYesNo && (
          <div className="flex gap-2 mb-2">
            <button
              type="button"
              onClick={() => send("yes")}
              disabled={loading}
              className="flex-1 bg-green-600 text-white rounded-full py-2 text-sm font-medium disabled:opacity-40"
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => send("no")}
              disabled={loading}
              className="flex-1 bg-white border border-slate-300 text-slate-700 rounded-full py-2 text-sm font-medium disabled:opacity-40"
            >
              No
            </button>
          </div>
        )}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={awaitingYesNo ? "Or type your answer…" : "Type your message…"}
            className="flex-1 border border-slate-300 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}

function Bubble({ role, text, decision, facts, muted }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-line ${
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : `bg-white text-slate-700 rounded-bl-sm border border-slate-200 ${
                muted ? "italic text-slate-400" : ""
              }`
        }`}
      >
        {text}

        {decision && (
          <details className="mt-2">
            <summary className="text-xs text-slate-400 cursor-pointer">
              What I understood / full derivation
            </summary>
            <div className="mt-2 text-xs text-slate-500">
              {facts && (
                <p className="mb-1">
                  Area: <strong>{facts.locality ? `${facts.locality} → ` : ""}{facts.zone_name}</strong>
                  {facts.ward != null && <> (ward {facts.ward})</>} · Tank:{" "}
                  <strong>{facts.tank_level_percent}%</strong>
                  {facts.days_since_delivery != null && (
                    <> · {facts.days_since_delivery} days since delivery</>
                  )}
                </p>
              )}
              {decision.proof_trace && (
                <pre className="whitespace-pre-wrap bg-slate-50 rounded p-2 mt-1">
                  {decision.proof_trace}
                </pre>
              )}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
