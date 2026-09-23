// Live delivery status, pinned below the conversation. Stays visible from
// the moment a report is accepted until the volunteer confirms the water
// arrived, so they never have to scroll back to find where things stand.

const STEPS = [
  { key: "scheduled", label: "Scheduled" },
  { key: "delivered", label: "Delivered" },
  { key: "confirmed", label: "Confirmed" },
];

// How far along each backend state is. "pending" sits before step 1
// because dispatch hasn't placed it yet.
const PROGRESS = {
  pending: -1,
  scheduled: 0,
  delivered: 1,
  confirmed: 2,
  not_received: 1,
};

export default function StatusCard({ status }) {
  const reached = PROGRESS[status.state] ?? -1;
  const failed = status.state === "not_received";

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide">Your request</p>
          <p className="text-base font-semibold text-slate-900">
            {status.area_label || status.zone_name.replace(/_/g, " ")}
          </p>
        </div>
        {status.high_priority && (
          <span className="bg-red-100 text-red-700 text-xs font-medium px-2 py-1 rounded">
            High priority
          </span>
        )}
      </div>

      {status.state === "pending" ? (
        <p className="text-sm text-slate-500 mt-3">
          Waiting for dispatch to assign a tanker. This page updates on its own.
        </p>
      ) : (
        <>
          <div className="flex items-center mt-4">
            {STEPS.map((step, i) => {
              const done = i <= reached;
              const isFailPoint = failed && i === 2;
              return (
                <div key={step.key} className="flex items-center flex-1 last:flex-none">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${
                        isFailPoint
                          ? "bg-red-100 text-red-600"
                          : done
                          ? "bg-blue-600 text-white"
                          : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      {isFailPoint ? "!" : done ? "✓" : i + 1}
                    </div>
                    <span
                      className={`text-[11px] mt-1 ${
                        done ? "text-slate-700" : "text-slate-400"
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className={`flex-1 h-0.5 mx-1 mb-4 ${
                        i < reached ? "bg-blue-600" : "bg-slate-200"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {status.slot && (
            <p className="text-sm text-slate-600 mt-3">
              Tanker <strong>{status.slot.tanker_id}</strong>, delivery slot{" "}
              <strong>{status.slot.slot}</strong> today.
            </p>
          )}

          {status.state === "delivered" && (
            <p className="text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2 mt-3">
              The driver marked this delivered — please confirm below whether the water
              actually arrived.
            </p>
          )}

          {status.state === "confirmed" && (
            <p className="text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2 mt-3">
              You confirmed the water arrived. Thank you.
            </p>
          )}

          {failed && (
            <p className="text-sm text-red-700 bg-red-50 rounded-lg px-3 py-2 mt-3">
              You reported the water did not arrive. Dispatch has been notified.
            </p>
          )}
        </>
      )}
    </div>
  );
}
