import { useState, useEffect } from "react";
import RouteMap, { BASEMAPS } from "./RouteMap";

const API_BASE = "http://localhost:8000";
const TANKERS = ["T1", "T2", "T3", "T4", "T5"];

export default function App() {
  const [tankerId, setTankerId] = useState("T1");
  const [deliveries, setDeliveries] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [basemap, setBasemap] = useState("street");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadRoute = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/driver/routes/${id}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not load route.");
      setDeliveries(data.deliveries);
      // Default to the first delivery that isn't done yet.
      const next = data.deliveries.find((d) => !d.completed) ?? data.deliveries[0];
      setSelectedSlot(next ? next.slot : null);
    } catch (err) {
      setError(err.message);
      setDeliveries([]);
      setSelectedSlot(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoute(tankerId);
  }, [tankerId]);

  const toggleComplete = async (slot, completed) => {
    // Optimistic update so the button feels instant; reconciled by the
    // reload below.
    setDeliveries((ds) => ds.map((d) => (d.slot === slot ? { ...d, completed } : d)));
    try {
      const res = await fetch(`${API_BASE}/api/driver/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tanker_id: tankerId, slot, completed }),
      });
      if (!res.ok) throw new Error("Could not update. Please try again.");
      await loadRoute(tankerId);
    } catch (err) {
      setError(err.message);
      await loadRoute(tankerId);
    }
  };

  const selected = deliveries.find((d) => d.slot === selectedSlot) ?? null;
  const doneCount = deliveries.filter((d) => d.completed).length;

  return (
    <div className="h-screen flex flex-col bg-slate-900 text-white">
      <header className="px-4 py-3 border-b border-slate-700 flex items-center gap-3">
        <div className="flex-1">
          <h1 className="text-base font-semibold">Today's route</h1>
          <p className="text-xs text-slate-400">
            {deliveries.length === 0
              ? "No deliveries assigned"
              : `${doneCount} of ${deliveries.length} delivered`}
          </p>
        </div>
        <select
          value={tankerId}
          onChange={(e) => setTankerId(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-sm"
        >
          {TANKERS.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </header>

      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-950 border border-red-800 text-red-300 text-sm rounded-md">
          {error}
        </div>
      )}

      <div className="relative flex-1 min-h-0">
        <RouteMap delivery={selected} basemap={basemap} />

        <div className="absolute top-2 right-2 z-[1000] flex rounded-md overflow-hidden shadow text-xs">
          {Object.entries(BASEMAPS).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => setBasemap(key)}
              className={`px-3 py-1.5 ${
                basemap === key ? "bg-blue-600 text-white" : "bg-white text-slate-700"
              }`}
            >
              {cfg.label}
            </button>
          ))}
        </div>

        {selected && (
          <div className="absolute bottom-2 left-2 z-[1000] bg-slate-800/95 rounded-lg px-3 py-2 text-xs">
            <p className="text-slate-300">
              Refill at{" "}
              <strong className="text-white">{selected.station_label ?? selected.station_name}</strong>
              , then drive to{" "}
              <strong className="text-white">{selected.zone_label ?? selected.zone_name}</strong>
            </p>
            {selected.distance_m != null &&
              (selected.distance_m < 100 ? (
                // The filling point sits inside the delivery area itself
                // (e.g. Manali), so there is no route line to draw.
                <p className="text-slate-400 mt-0.5">
                  The filling point is in this area — no drive needed after refilling.
                </p>
              ) : (
                <p className="text-slate-400 mt-0.5">
                  Shortest route: {(selected.distance_m / 1000).toFixed(1)} km
                </p>
              ))}
          </div>
        )}
      </div>

      <div className="max-h-[42%] overflow-y-auto border-t border-slate-700">
        {loading && <p className="text-slate-400 text-sm p-4">Loading...</p>}

        {!loading && deliveries.length === 0 && !error && (
          <p className="text-slate-400 text-sm p-4">
            No deliveries for {tankerId} today. Ask dispatch to generate the schedule.
          </p>
        )}

        <div className="p-3 space-y-2">
          {deliveries.map((d) => {
            const isSelected = d.slot === selectedSlot;
            return (
              <div
                key={d.slot}
                onClick={() => setSelectedSlot(d.slot)}
                className={`rounded-lg p-3 border cursor-pointer transition-colors ${
                  isSelected ? "border-blue-500 bg-slate-800" : "border-slate-700 bg-slate-800/60"
                } ${d.completed ? "opacity-55" : ""}`}
              >
                <div className="flex justify-between items-start gap-3">
                  <div className="min-w-0">
                    <p className="text-xs text-slate-400">Slot {d.slot}</p>
                    <p className={`text-base font-medium ${d.completed ? "line-through" : ""}`}>
                      {d.zone_label ?? d.zone_name}
                    </p>
                    {d.volunteer_request && (
                      <p className="text-xs text-violet-300">Reported by a ward volunteer</p>
                    )}
                    <p className="text-sm text-slate-400 mt-0.5">
                      {d.need_liters.toLocaleString()} L
                      {d.distance_m != null && <> · {(d.distance_m / 1000).toFixed(1)} km</>}
                      {d.is_high_priority && (
                        <span className="ml-2 text-red-400 font-medium">High priority</span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleComplete(d.slot, !d.completed);
                    }}
                    className={`shrink-0 px-3 py-1.5 rounded-md text-xs font-medium ${
                      d.completed ? "bg-slate-700 text-slate-300" : "bg-green-600 text-white"
                    }`}
                  >
                    {d.completed ? "Undo" : "Mark delivered"}
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
