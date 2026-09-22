import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from "react-leaflet";

const BASEMAPS = {
  street: {
    label: "Street",
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "&copy; OpenStreetMap contributors",
  },
  satellite: {
    label: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri",
    labelsUrl:
      "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
  },
};

// Refits the viewport whenever the selected delivery changes, so the whole
// route is always in frame without the driver panning around.
function FitRoute({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords && coords.length > 1) {
      map.fitBounds(coords, { padding: [40, 40] });
    }
  }, [coords, map]);
  return null;
}

export default function RouteMap({ delivery, basemap }) {
  const cfg = BASEMAPS[basemap] ?? BASEMAPS.street;
  const route = delivery?.route_coords ?? [];
  const center = delivery?.zone_coords ?? [13.06, 80.25];

  return (
    <MapContainer center={center} zoom={13} className="h-full w-full">
      <TileLayer key={basemap} url={cfg.url} attribution={cfg.attribution} maxZoom={19} />
      {cfg.labelsUrl && <TileLayer key={`${basemap}-labels`} url={cfg.labelsUrl} maxZoom={19} />}

      {route.length > 1 && (
        <>
          <Polyline positions={route} pathOptions={{ color: "#22c55e", weight: 5, opacity: 0.9 }} />
          <FitRoute coords={route} />
        </>
      )}

      {delivery?.station_coords && (
        <CircleMarker
          center={delivery.station_coords}
          radius={8}
          pathOptions={{ color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.9 }}
        >
          <Popup>Refill here first: {delivery.station_name}</Popup>
        </CircleMarker>
      )}

      {delivery?.zone_coords && (
        <CircleMarker
          center={delivery.zone_coords}
          radius={9}
          pathOptions={{
            color: delivery.is_high_priority ? "#dc2626" : "#16a34a",
            fillColor: delivery.is_high_priority ? "#dc2626" : "#16a34a",
            fillOpacity: 0.9,
          }}
        >
          <Popup>Deliver to: {delivery.zone_name}</Popup>
        </CircleMarker>
      )}
    </MapContainer>
  );
}

export { BASEMAPS };
