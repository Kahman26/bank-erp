import { Tooltip, Typography } from "antd";
import type { ReactNode } from "react";

/** Величины — один оттенок бренда; цвет не кодирует ранг. */
const BAR = "#1F4E79";
const TRACK = "#F0F2F5";

export interface BarItem {
  key: string;
  label: ReactNode;
  value: number;
  tooltip?: ReactNode;
  extra?: ReactNode;
}

/** Горизонтальные столбики с подписью значения в конце (подписи — цветом текста, не столбика). */
export function BarList({ items, max }: { items: BarItem[]; max?: number }) {
  const top = max ?? Math.max(1, ...items.map((i) => i.value));
  return (
    <div style={{ display: "grid", gap: 6 }}>
      {items.map((i) => (
        <Tooltip key={i.key} title={i.tooltip} placement="topLeft">
          <div style={{ display: "grid", gridTemplateColumns: "minmax(110px, 38%) 1fr auto", alignItems: "center", gap: 10, padding: "2px 0" }}>
            <Typography.Text ellipsis style={{ fontSize: 13 }}>
              {i.label}
            </Typography.Text>
            <div style={{ background: TRACK, height: 10, borderRadius: "0 4px 4px 0" }}>
              <div
                style={{
                  width: `${(i.value / top) * 100}%`,
                  minWidth: i.value ? 2 : 0,
                  height: "100%",
                  background: BAR,
                  borderRadius: "0 4px 4px 0",
                }}
              />
            </div>
            <span style={{ fontVariantNumeric: "tabular-nums", fontSize: 13, minWidth: 36, textAlign: "right" }}>
              {i.value.toLocaleString("ru-RU")}
              {i.extra}
            </span>
          </div>
        </Tooltip>
      ))}
    </div>
  );
}

/** Вертикальные столбцы по времени: подписи периодов под осью, значения — в подсказке. */
export function Columns({ items, height = 160 }: { items: BarItem[]; height?: number }) {
  const top = Math.max(1, ...items.map((i) => i.value));
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height, borderBottom: "1px solid #D9D9D9" }}>
        {items.map((i) => (
          <Tooltip key={i.key} title={i.tooltip}>
            {/* зона наведения — на всю высоту колонки, а не только столбик */}
            <div style={{ flex: 1, height: "100%", display: "flex", alignItems: "flex-end", cursor: "default" }}>
              <div style={{ width: "100%", height: `${(i.value / top) * 100}%`, minHeight: i.value ? 2 : 0, background: BAR, borderRadius: "4px 4px 0 0" }} />
            </div>
          </Tooltip>
        ))}
      </div>
      <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
        {items.map((i) => (
          <div key={i.key} style={{ flex: 1, textAlign: "center", fontSize: 11, color: "#8C8C8C", overflow: "hidden", whiteSpace: "nowrap" }}>
            {i.label}
          </div>
        ))}
      </div>
    </div>
  );
}

export interface Segment {
  key: string;
  label: string;
  value: number;
  color: string;
}

/** Доли целого: одна полоса из сегментов с зазором 2 px + легенда со значениями (цвет не единственный носитель). */
export function StackedBar({ segments }: { segments: Segment[] }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  const shown = segments.filter((s) => s.value > 0);
  return (
    <>
      <div style={{ display: "flex", gap: 2, height: 14, marginBottom: 12 }}>
        {shown.map((s, idx) => (
          <Tooltip key={s.key} title={`${s.label}: ${s.value} (${((s.value / total) * 100).toFixed(1)} %)`}>
            <div
              style={{
                width: `${(s.value / total) * 100}%`,
                minWidth: 3,
                background: s.color,
                borderRadius: idx === 0 ? "4px 0 0 4px" : idx === shown.length - 1 ? "0 4px 4px 0" : 0,
              }}
            />
          </Tooltip>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: "4px 16px" }}>
        {segments.map((s) => (
          <div key={s.key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: s.color, flex: "none" }} />
            <span style={{ flex: 1 }}>{s.label}</span>
            <span style={{ fontVariantNumeric: "tabular-nums" }}>{s.value.toLocaleString("ru-RU")}</span>
            <span style={{ color: "#8C8C8C", width: 44, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
              {((s.value / total) * 100).toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
