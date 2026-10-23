import { Tag } from "antd";

/** Цвет статуса — общий для таблицы, карточки и меток на карте. */
export const STATUS_COLORS: Record<string, string> = {
  in_service: "#389e0d",
  repair: "#fa8c16",
  vendor_repair: "#d4380d",
  installing: "#1677ff",
  in_delivery: "#13c2c2",
  in_stock: "#2f54eb",
  on_farm: "#722ed1",
  to_writeoff: "#d48806",
  written_off: "#8c8c8c",
};

export function StatusTag({ code, name }: { code: string; name: string }) {
  return (
    <Tag color={STATUS_COLORS[code] ?? "default"} style={{ marginInlineEnd: 0 }}>
      {name}
    </Tag>
  );
}
