import { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from "react-leaflet";
import { ZONE_COORDS, SOURCE_STATIONS, MAP_CENTER } from "../zonesData";

const BASEMAPS = {
  street: {
    label: "Street",
    // Standard OSM tiles -- labeled roads, place names, colored land use at
    // every zoom, closest free/keyless look to Google Maps' default style.
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  },
  satellite: {
    label: "Satellite",
    // Esri World Imagery -- free, no API key required.
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
    maxZoom: 19,
    // Transparent overlay with place names/roads/boundaries, same idea as
    // Google Maps' "Hybrid" mode -- satellite imagery alone has no text.
    labelsUrl:
      "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
  },
};

export default function DispatchMap({ schedule, zones }) {
  const [basemap, setBasemap] = useState("street");
  const highPriorityZones = new Set(zones.filter((z) => z.is_high_priority).map((z) => z.name));
  const scheduledZones = new Set(
    schedule.flatMap((row) => row.slots).filter((v) => v !== null)
  );
  const active = BASEMAPS[basemap];

  return (
    <div className="relative h-full w-full">
      <div className="absolute top-2 right-2 z-[1000] flex rounded-md overflow-hidden shadow bg-white text-xs">
        {Object.entries(BASEMAPS).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setBasemap(key)}
            className={`px-3 py-1.5 ${
              basemap === key ? "bg-blue-600 text-white" : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            {cfg.label}
          </button>
        ))}
      </div>

      <MapContainer center={MAP_CENTER} zoom={11} className="h-full w-full rounded-lg">
        <TileLayer key={basemap} url={active.url} attribution={active.attribution} maxZoom={active.maxZoom} />
        {active.labelsUrl && (
          <TileLayer key={`${basemap}-labels`} url={active.labelsUrl} maxZoom={active.maxZoom} />
        )}

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
    </div>
  );
}
