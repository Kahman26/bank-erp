import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

const pin = L.divIcon({
  className: "atm-dot",
  html: '<span style="background:#1F4E79;width:18px;height:18px"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

function ClickHandler({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) });
  return null;
}

function Recenter({ lat, lon, zoom }: { lat: number; lon: number; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], zoom);
  }, [map, lat, lon, zoom]);
  return null;
}

/** В модальном окне карта создаётся до окончания анимации — пересчитываем размер, иначе тайлы серые. */
function FixSize() {
  const map = useMap();
  useEffect(() => {
    const timers = [100, 400].map((ms) => setTimeout(() => map.invalidateSize(), ms));
    return () => timers.forEach(clearTimeout);
  }, [map]);
  return null;
}

/** Выбор точки кликом по карте. Координаты можно и ввести вручную — карта подхватит. */
export default function LocationPicker(props: {
  lat?: number | null;
  lon?: number | null;
  center: [number, number];
  onPick: (lat: number, lon: number) => void;
}) {
  const has = props.lat != null && props.lon != null;
  const center: [number, number] = has ? [props.lat!, props.lon!] : props.center;
  return (
    <MapContainer center={center} zoom={has ? 16 : 12} style={{ height: 260, width: "100%", borderRadius: 8, cursor: "crosshair" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onPick={props.onPick} />
      {has && <Marker position={[props.lat!, props.lon!]} icon={pin} />}
      {!has && <Recenter lat={props.center[0]} lon={props.center[1]} zoom={12} />}
      <FixSize />
    </MapContainer>
  );
}
