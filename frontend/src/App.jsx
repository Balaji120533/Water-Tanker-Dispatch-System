import { useState, useCallback } from "react";
import DispatchMap from "./components/DispatchMap";
import ScheduleTable from "./components/ScheduleTable";
import { generateSchedule, disruptBreakdown, disruptUrgent } from "./api";

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [changedCells, setChangedCells] = useState(new Set());
  const [lastDiff, setLastDiff] = useState(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    setChangedCells(new Set());
    setLastDiff(null);
    try {
      const result = await generateSchedule();
      setData(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const applyDisruption = useCallback(async (fn) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      setData(result);
      setLastDiff(result.diff);
      const cells = new Set(result.diff.map((d) => `${d.tanker_id}-${d.slot}`));
      setChangedCells(cells);
      setTimeout(() => setChangedCells(new Set()), 2500);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const unscheduledZones =
    data?.zones.filter(
      (z) => !data.schedule.some((row) => row.slots.includes(z.name))
    ) ?? [];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">
        Water Tanker Dispatch — Dispatcher Dashboard
      </h1>
      <p className="text-sm text-gray-500 mb-6">
        Validated simulation. Solver decisions come from the CSP module; this UI only displays and triggers them.
      </p>

      <div className="flex flex-wrap gap-3 mb-6">
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium disabled:opacity-50"
        >
          Generate schedule
        </button>

        {data && (
          <>
            <TankerBreakdownControl
              tankers={data.schedule.map((r) => r.tanker_id)}
              onTrigger={(id) => applyDisruption(() => disruptBreakdown(id))}
              disabled={loading}
            />
            <UrgentRequestControl
              zones={unscheduledZones.map((z) => z.name)}
              onTrigger={(name) => applyDisruption(() => disruptUrgent(name))}
              disabled={loading}
            />
          </>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
          {error}
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-4 h-[500px]">
            <DispatchMap schedule={data.schedule} zones={data.zones} />
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="text-lg font-medium mb-3">Today's schedule</h2>
            <ScheduleTable
              schedule={data.schedule}
              numSlots={data.num_slots}
              changedCells={changedCells}
            />
            {lastDiff && (
              <div className="mt-4 text-sm">
                <h3 className="font-medium mb-1">Last repair diff</h3>
                {lastDiff.length === 0 ? (
                  <p className="text-gray-400">No changes needed.</p>
                ) : (
                  <ul className="space-y-1">
                    {lastDiff.map((d, i) => (
                      <li key={i} className="text-gray-600">
                        {d.tanker_id} slot {d.slot}: {d.from ?? "idle"} → {d.to ?? "idle"}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TankerBreakdownControl({ tankers, onTrigger, disabled }) {
  const [selected, setSelected] = useState(tankers[0] ?? "");
  return (
    <div className="flex items-center gap-2">
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="border border-gray-300 rounded-md px-2 py-2 text-sm"
      >
        {tankers.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
      <button
        onClick={() => onTrigger(selected)}
        disabled={disabled}
        className="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium disabled:opacity-50"
      >
        Mark tanker unavailable
      </button>
    </div>
  );
}

function UrgentRequestControl({ zones, onTrigger, disabled }) {
  const [selected, setSelected] = useState(zones[0] ?? "");

  if (zones.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <select
        value={selected || zones[0]}
        onChange={(e) => setSelected(e.target.value)}
        className="border border-gray-300 rounded-md px-2 py-2 text-sm"
      >
        {zones.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      <button
        onClick={() => onTrigger(selected || zones[0])}
        disabled={disabled}
        className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm font-medium disabled:opacity-50"
      >
        Escalate to urgent
      </button>
    </div>
  );
}
