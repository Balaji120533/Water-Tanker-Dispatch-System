import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from "react-leaflet";
import { ZONE_COORDS, SOURCE_STATIONS, MAP_CENTER } from "../zonesData";

export default function DispatchMap({ schedule, zones }) {
  const highPriorityZones = new Set(zones.filter((z) => z.is_high_priority).map((z) => z.name));
  const scheduledZones = new Set(
    schedule.flatMap((row) => row.slots).filter((v) => v !== null)
  );

  return (
    <MapContainer center={MAP_CENTER} zoom={11} className="h-full w-full rounded-lg">
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution="&copy; OpenStreetMap contributors &copy; CARTO"
      />

      {Object.entries(SOURCE_STATIONS).map(([name, pos]) => (
        <CircleMarker
          key={name}
          center={pos}
          radius={7}
          pathOptions={{ color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.8 }}
        >
          <Popup>Source station: {name}</Popup>
        </CircleMarker>
      ))}

      {Object.entries(ZONE_COORDS).map(([name, pos]) => {
        const scheduled = scheduledZones.has(name);
        const highPriority = highPriorityZones.has(name);
        const color = !scheduled ? "#9ca3af" : highPriority ? "#dc2626" : "#16a34a";
        return (
          <CircleMarker
            key={name}
            center={pos}
            radius={8}
            pathOptions={{ color, fillColor: color, fillOpacity: 0.85 }}
          >
            <Popup>
              <div className="text-sm">
                <strong>{name}</strong>
                <div>{highPriority ? "High priority" : "Entitled"}</div>
                <div>{scheduled ? "Scheduled today" : "Not scheduled"}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
