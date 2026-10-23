import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Table, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";

interface Change {
  field: string;
  label: string;
  old: unknown;
  new: unknown;
}

export interface AuditRow {
  id: number;
  at: string;
  user: string | null;
  entity: string;
  entity_label: string;
  entity_id: number | null;
  atm_id: number | null;
  atm_code: string | null;
  action: string;
  action_label: string;
  changes: Change[];
}

const ACTION_COLORS: Record<string, string> = {
  create: "green",
  update: "blue",
  delete: "red",
  login: "default",
  login_fail: "orange",
  lock: "red",
};

function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "да" : "нет";
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}/.test(v)) {
    const d = dayjs(v);
    return v.length > 10 ? d.format("DD.MM.YYYY HH:mm") : d.format("DD.MM.YYYY");
  }
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

/** Журнал изменений по параметрам запроса; строка раскрывается в таблицу «поле — было — стало». */
export default function AuditTable({ query, hideAtm }: { query: string; hideAtm?: boolean }) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const q = `${query}${query ? "&" : ""}page=${page}&page_size=${pageSize}`;
  const { data, isFetching } = useQuery({
    queryKey: ["audit", q],
    queryFn: () => api.get<{ items: AuditRow[]; total: number }>(`/audit?${q}`),
    placeholderData: keepPreviousData,
  });

  return (
    <Table<AuditRow>
      rowKey="id"
      size="small"
      loading={isFetching}
      dataSource={data?.items}
      scroll={{ x: 800 }}
      pagination={{
        current: page,
        pageSize,
        total: data?.total,
        showSizeChanger: true,
        hideOnSinglePage: true,
        onChange: (p, s) => {
          setPage(p);
          setPageSize(s);
        },
      }}
      expandable={{
        rowExpandable: (r) => r.changes.length > 0,
        expandedRowRender: (r) => (
          <Table<Change>
            rowKey="field"
            size="small"
            pagination={false}
            dataSource={r.changes}
            columns={[
              { title: "Поле", dataIndex: "label", width: 220 },
              ...(r.action === "update" || r.action === "delete"
                ? [{ title: "Было", dataIndex: "old", render: (v: unknown) => <Typography.Text delete={r.action === "update"}>{show(v)}</Typography.Text> }]
                : []),
              ...(r.action !== "delete" ? [{ title: r.action === "update" ? "Стало" : "Значение", dataIndex: "new", render: show }] : []),
            ]}
          />
        ),
      }}
      columns={[
        { title: "Когда", dataIndex: "at", width: 140, render: (v) => dayjs(v).format("DD.MM.YYYY HH:mm") },
        { title: "Кто", dataIndex: "user", width: 180, render: (v) => v ?? <Typography.Text type="secondary">система</Typography.Text> },
        {
          title: "Действие",
          width: 150,
          render: (_, r) => <Tag color={ACTION_COLORS[r.action] ?? "default"}>{r.action_label}</Tag>,
        },
        { title: "Объект", dataIndex: "entity_label", width: 150 },
        ...(hideAtm
          ? []
          : [
              {
                title: "Банкомат",
                width: 140,
                render: (_: unknown, r: AuditRow) => (r.atm_id ? <Link to={`/atms/${r.atm_id}`}>{r.atm_code ?? r.atm_id}</Link> : "—"),
              },
            ]),
        {
          title: "Что изменилось",
          render: (_, r) =>
            r.action === "update"
              ? r.changes.map((c) => c.label).join(", ")
              : r.entity === "auth"
                ? r.changes.map((c) => `${c.label}: ${show(c.new)}`).join(", ")
                : `полей: ${r.changes.length}`,
        },
      ]}
    />
  );
}
