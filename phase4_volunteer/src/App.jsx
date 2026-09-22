import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000";

const CONDITION_LABELS = {
  empty: "Empty",
  very_low: "Very low",
  low: "Low",
  ok: "OK, some water left",
  full: "Full",
};

export default function App() {
  const [zones, setZones] = useState([]);
  const [conditions, setConditions] = useState([]);
  const [zone, setZone] = useState("");
  const [condition, setCondition] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/volunteer/zones`)
      .then((r) => r.json())
      .then((data) => {
        setZones(data.zones);
        setConditions(data.conditions);
        setZone(data.zones[0] ?? "");
        setCondition(data.conditions[0] ?? "");
      })
      .catch(() => setError("Could not reach the dispatch system. Try again shortly."));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/volunteer/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ zone_name: zone, condition }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "Something went wrong. Please try again.");
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-blue-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-md p-6 w-full max-w-md">
        <h1 className="text-xl font-semibold text-gray-900 mb-1">Report water condition</h1>
        <p className="text-sm text-gray-500 mb-6">
          Tell us about your area's water tank so we can check if you're due a delivery.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your area</label>
            <select
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              {zones.map((z) => (
                <option key={z} value={z}>
                  {z}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              How much water is left in the tank?
            </label>
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              {conditions.map((c) => (
                <option key={c} value={c}>
                  {CONDITION_LABELS[c] ?? c}
                </option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={loading || !zone || !condition}
            className="w-full bg-blue-600 text-white rounded-md py-2.5 text-sm font-medium disabled:opacity-50"
          >
            {loading ? "Checking..." : "Submit report"}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
            {error}
          </div>
        )}

        {result && <ResultCard result={result} />}
      </div>
    </div>
  );
}

function ResultCard({ result }) {
  const badgeColor = !result.entitled
    ? "bg-gray-100 text-gray-700"
    : result.high_priority
    ? "bg-red-100 text-red-700"
    : "bg-green-100 text-green-700";

  const badgeText = !result.entitled
    ? "Not currently entitled"
    : result.high_priority
    ? "High priority"
    : "Entitled";

  return (
    <div className="mt-5 border border-gray-200 rounded-lg p-4">
      <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${badgeColor}`}>
        {badgeText}
      </span>

      <p className="text-sm text-gray-700 mt-3">
        {result.entitled
          ? `${result.zone_name} qualifies for a water delivery based on the reported condition.`
          : `Based on the reported condition, ${result.zone_name} does not currently meet the entitlement criteria.`}
      </p>

      {result.entitled && (
        <p className="text-sm text-gray-600 mt-2">
          {result.estimated_slot
            ? `Scheduled today: tanker ${result.estimated_slot.tanker_id}, slot ${result.estimated_slot.slot}.`
            : result.estimated_slot_note}
        </p>
      )}

      <details className="mt-3">
        <summary className="text-xs text-gray-400 cursor-pointer">Why? (technical explanation)</summary>
        <pre className="text-xs text-gray-500 mt-2 whitespace-pre-wrap">{result.reason}</pre>
      </details>
    </div>
  );
}
