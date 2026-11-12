import { Tag } from "antd";

import { brand } from "@/theme/brand";

import { STATUS_COLORS } from "./statusColors";

export function StatusTag({ code, name }: { code: string; name: string }) {
  const color = STATUS_COLORS[code] ?? "#666666";
  return (
    <Tag className="atm-status" style={{ marginInlineEnd: 0, color: code === "in_service" ? brand.greenHover : color, background: color + "14" }}>
      <span className="atm-status-dot" style={{ background: color }} aria-hidden="true" />
      {name}
    </Tag>
  );
}
