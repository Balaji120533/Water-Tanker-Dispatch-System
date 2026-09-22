import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000";

export default function App() {
  const [tankerId, setTankerId] = useState("T1");
  const [deliveries, setDeliveries] = useState([]);
  const [completed, setCompleted] = useState(new Set());
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadRoute = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/driver/routes/${id}`);
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "Could not load route.");
      }
      const data = await res.json();
      setDeliveries(data.deliveries);
      setCompleted(new Set());
    } catch (err) {
      setError(err.message);
      setDeliveries([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoute(tankerId);
  }, []);

  const toggleComplete = (slot) => {
    setCompleted((prev) => {
      const next = new Set(prev);
      if (next.has(slot)) next.delete(slot);
      else next.add(slot);
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <div className="max-w-sm mx-auto">
        <h1 className="text-lg font-semibold mb-4">Today's route</h1>

        <div className="flex gap-2 mb-6">
          <select
            value={tankerId}
            onChange={(e) => setTankerId(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm"
          >
            {["T1", "T2", "T3", "T4", "T5"].map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
          <button
            onClick={() => loadRoute(tankerId)}
            className="bg-blue-600 rounded-md px-4 py-2 text-sm font-medium"
          >
            Load
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-950 border border-red-800 text-red-300 text-sm rounded-md">
            {error}
          </div>
        )}

        {loading && <p className="text-gray-400 text-sm">Loading...</p>}

        {!loading && deliveries.length === 0 && !error && (
          <p className="text-gray-400 text-sm">No deliveries scheduled for {tankerId} today.</p>
        )}

        <div className="space-y-3">
          {deliveries.map((d) => {
            const isDone = completed.has(d.slot);
            return (
              <div
                key={d.slot}
                className={`rounded-lg p-4 border ${
                  isDone ? "bg-gray-800 border-gray-700 opacity-60" : "bg-gray-800 border-gray-600"
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-xs text-gray-400">Slot {d.slot}</p>
                    <p className="text-base font-medium">{d.zone_name}</p>
                    <p className="text-sm text-gray-400 mt-1">
                      {d.need_liters.toLocaleString()} L
                      {d.is_high_priority && (
                        <span className="ml-2 text-red-400 font-medium">High priority</span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={() => toggleComplete(d.slot)}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium ${
                      isDone ? "bg-gray-700 text-gray-300" : "bg-green-600 text-white"
                    }`}
                  >
                    {isDone ? "Undo" : "Mark complete"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
