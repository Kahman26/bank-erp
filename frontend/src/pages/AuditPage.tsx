import { useQuery } from "@tanstack/react-query";
import { Card, DatePicker, Select, Space, Typography } from "antd";
import dayjs from "dayjs";
import { useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import AuditTable from "@/audit/AuditTable";

type Option = { value: string | number; label: string };

export default function AuditPage() {
  const [params, setParams] = useSearchParams();
  const { data: meta } = useQuery({
    queryKey: ["audit-meta"],
    queryFn: () => api.get<{ entities: Option[]; actions: Option[]; users: Option[] }>("/audit/meta"),
  });

  const set = (key: string, value: string | string[] | undefined) => {
    const next = new URLSearchParams(params);
    next.delete(key);
    for (const v of Array.isArray(value) ? value : value ? [value] : []) next.append(key, v);
    setParams(next, { replace: true });
  };
  const from = params.get("date_from");
  const to = params.get("date_to");

  return (
    <Card title="Журнал изменений">
      <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
        Кто, что и когда изменил в справочнике, а также входы в систему и неудачные попытки входа.
      </Typography.Paragraph>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select
          mode="multiple"
          allowClear
          placeholder="Объект"
          style={{ minWidth: 200 }}
          value={params.getAll("entity")}
          onChange={(v: string[]) => set("entity", v)}
          options={meta?.entities}
        />
        <Select
          mode="multiple"
          allowClear
          placeholder="Действие"
          style={{ minWidth: 180 }}
          value={params.getAll("action")}
          onChange={(v: string[]) => set("action", v)}
          options={meta?.actions}
        />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Пользователь"
          style={{ minWidth: 220 }}
          value={params.get("user_id") ? Number(params.get("user_id")) : undefined}
          onChange={(v?: number) => set("user_id", v ? String(v) : undefined)}
          options={meta?.users}
        />
        <DatePicker.RangePicker
          format="DD.MM.YYYY"
          value={[from ? dayjs(from) : null, to ? dayjs(to) : null]}
          onChange={(range) => {
            const next = new URLSearchParams(params);
            next.delete("date_from");
            next.delete("date_to");
            if (range?.[0]) next.set("date_from", range[0].format("YYYY-MM-DD"));
            if (range?.[1]) next.set("date_to", range[1].format("YYYY-MM-DD"));
            setParams(next, { replace: true });
          }}
        />
      </Space>
      <AuditTable query={params.toString()} />
    </Card>
  );
}
