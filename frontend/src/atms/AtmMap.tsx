import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import { Link } from "react-router-dom";

import { STATUS_COLORS } from "./status";

export type Point = [number, string, number, number, string];

const UZ_CENTER: [number, number] = [41.3, 64.5];

const iconCache = new Map<string, L.DivIcon>();
function dotIcon(status: string): L.DivIcon {
  let icon = iconCache.get(status);
  if (!icon) {
    icon = L.divIcon({
      className: "atm-dot",
      html: `<span style="background:${STATUS_COLORS[status] ?? "#595959"}"></span>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    });
    iconCache.set(status, icon);
  }
  return icon;
}

function FitBounds({ points }: { points: Point[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView([points[0][2], points[0][3]], 15);
      return;
    }
    map.fitBounds(L.latLngBounds(points.map((p) => [p[2], p[3]] as [number, number])), { padding: [30, 30], maxZoom: 15 });
  }, [map, points]);
  return null;
}

/** Карта банкоматов: кластеры при отдалении, цвет метки — статус. */
export default function AtmMap({
  points,
  statusNames,
  height,
  popupExtra,
}: {
  points: Point[];
  statusNames: Record<string, string>;
  height: number | string;
  popupExtra?: boolean;
}) {
  const markers = useMemo(
    () =>
      points.map(([id, code, lat, lon, status]) => (
        <Marker key={id} position={[lat, lon]} icon={dotIcon(status)}>
          {popupExtra !== false && (
            <Popup>
              <b>{code}</b>
              <br />
              {statusNames[status] ?? status}
              <br />
              <Link to={`/atms/${id}`}>Открыть карточку</Link>
            </Popup>
          )}
        </Marker>
      )),
    [points, statusNames, popupExtra],
  );

  return (
    <MapContainer center={UZ_CENTER} zoom={6} style={{ height, width: "100%", borderRadius: 8 }} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MarkerClusterGroup chunkedLoading maxClusterRadius={45}>
        {markers}
      </MarkerClusterGroup>
      <FitBounds points={points} />
    </MapContainer>
  );
}
