import { Tag } from "antd";

import { STATUS_COLORS } from "./statusColors";

export function StatusTag({ code, name }: { code: string; name: string }) {
  return (
    <Tag color={STATUS_COLORS[code] ?? "default"} style={{ marginInlineEnd: 0 }}>
      {name}
    </Tag>
  );
}
