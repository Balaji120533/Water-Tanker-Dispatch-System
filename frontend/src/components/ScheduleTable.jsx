export default function ScheduleTable({ schedule, numSlots, changedCells }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="border-b border-gray-300 text-left">
          <th className="py-2 pr-4">Tanker</th>
          <th className="py-2 pr-4">Capacity</th>
          {Array.from({ length: numSlots }, (_, i) => (
            <th key={i} className="py-2 pr-4">
              Slot {i}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {schedule.map((row) => (
          <tr key={row.tanker_id} className="border-b border-gray-100">
            <td className="py-2 pr-4 font-medium">{row.tanker_id}</td>
            <td className="py-2 pr-4 text-gray-500">{row.capacity_liters}L</td>
            {row.slots.map((zone, slot) => {
              const cellKey = `${row.tanker_id}-${slot}`;
              const changed = changedCells?.has(cellKey);
              return (
                <td
                  key={slot}
                  className={`py-2 pr-4 transition-colors duration-700 rounded ${
                    changed ? "bg-yellow-200" : ""
                  }`}
                >
                  {zone ?? <span className="text-gray-300">idle</span>}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
