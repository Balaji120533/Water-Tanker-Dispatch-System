// Volunteer reports the entitlement engine approved, with where they are
// in the schedule and which filling point serves them.

const STATE_STYLE = {
  pending: "bg-amber-100 text-amber-800",
  scheduled: "bg-blue-100 text-blue-800",
  delivered: "bg-emerald-100 text-emerald-800",
  confirmed: "bg-emerald-100 text-emerald-800",
  not_received: "bg-red-100 text-red-700",
};

const STATE_LABEL = {
  pending: "Waiting for a slot",
  scheduled: "Scheduled",
  delivered: "Delivered — awaiting volunteer",
  confirmed: "Volunteer confirmed",
  not_received: "Volunteer says NOT received",
};

export default function VolunteerRequests({ requests }) {
  return (
    <ul className="space-y-2">
      {requests.map((r) => (
        <li key={r.id} className="border border-gray-200 rounded-md p-2 text-sm">
          <div className="flex items-start justify-between gap-2">
            <div>
              <span className="font-medium text-gray-900">{r.area_label}</span>
              {r.high_priority && (
                <span className="ml-2 text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
                  High priority
                </span>
              )}
            </div>
            <span className={`text-xs px-1.5 py-0.5 rounded whitespace-nowrap ${STATE_STYLE[r.state]}`}>
              {STATE_LABEL[r.state] ?? r.state}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Tank {r.tank_level_percent}%
            {r.slot && <> · {r.slot.tanker_id}, slot {r.slot.slot}</>}
            {r.station_label && (
              <>
                {" "}· refill at {r.station_label}
                {r.distance_m != null && <> ({(r.distance_m / 1000).toFixed(1)} km by road)</>}
              </>
            )}
            {r.route_to_zone_centre && <> · route to zone centre until the road map loads</>}
          </p>
        </li>
      ))}
    </ul>
  );
}
