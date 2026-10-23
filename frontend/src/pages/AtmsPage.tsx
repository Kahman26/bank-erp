import { EnvironmentOutlined, PlusOutlined } from "@ant-design/icons";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button, Card, Input, Space, Table, Tag, Tooltip, Typography } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import dayjs from "dayjs";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type { AtmModel } from "@/api/types";
import AtmForm from "@/atms/AtmForm";
import FilterPanel, { filterParams } from "@/atms/FilterPanel";
import { StatusTag } from "@/atms/status";
import type { AtmPage, AtmRow } from "@/atms/types";
import { useAuth } from "@/auth/AuthContext";

const fmt = (d: string | null) => (d ? dayjs(d).format("DD.MM.YYYY") : "—");

export default function AtmsPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState(params.get("q") ?? "");

  const page = Number(params.get("page") ?? 1);
  const pageSize = Number(params.get("page_size") ?? 50);
  const query = params.toString();

  const { data, isFetching } = useQuery({
    queryKey: ["atms", query],
    queryFn: () => api.get<AtmPage>(`/atms?${query}`),
    placeholderData: keepPreviousData,
  });
  const { data: models } = useQuery({ queryKey: ["atm-models"], queryFn: () => api.get<AtmModel[]>("/atm-models") });

  const update = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(changes)) {
      if (v === undefined || v === "") next.delete(k);
      else next.set(k, v);
    }
    setParams(next, { replace: true });
  };

  const sortOrder = (key: string) =>
    params.get("sort") === key || (!params.get("sort") && key === "atm_code")
      ? params.get("order") === "desc"
        ? ("descend" as const)
        : ("ascend" as const)
      : null;

  return (
    <Card
      title="Банкоматы"
      extra={
        <Space wrap>
          <Button icon={<EnvironmentOutlined />} onClick={() => navigate(`/map?${filterParams(params)}`)}>
            На карте
          </Button>
          {can("edit") && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>
              Добавить
            </Button>
          )}
        </Space>
      }
    >
      <Input.Search
        allowClear
        placeholder="Код, Terminal ID, серийный номер, адрес"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onSearch={(v) => update({ q: v.trim() || undefined, page: undefined })}
        style={{ marginBottom: 12, maxWidth: 480 }}
        enterButton
      />
      <FilterPanel models={models} />
      <Typography.Text type="secondary" style={{ display: "block", marginBottom: 8 }}>
        Найдено: {data?.total ?? "…"}
      </Typography.Text>
      <Table<AtmRow>
        rowKey="id"
        size="middle"
        loading={isFetching}
        dataSource={data?.items}
        scroll={{ x: 1300 }}
        onRow={(r) => ({ onClick: () => navigate(`/atms/${r.id}`), style: { cursor: "pointer" } })}
        pagination={{
          current: page,
          pageSize,
          total: data?.total,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100, 200],
        }}
        onChange={(pg, _filters, sorter) => {
          const s = sorter as SorterResult<AtmRow>;
          update({
            page: String(pg.current ?? 1),
            page_size: String(pg.pageSize ?? 50),
            sort: s.order ? String(s.columnKey) : undefined,
            order: s.order === "descend" ? "desc" : undefined,
          });
        }}
        columns={[
          {
            title: "Код",
            key: "atm_code",
            dataIndex: "atm_code",
            sorter: true,
            sortOrder: sortOrder("atm_code"),
            fixed: "left",
            width: 140,
            render: (v, r) => (
              <Link to={`/atms/${r.id}`} onClick={(e) => e.stopPropagation()}>
                <b>{v}</b>
              </Link>
            ),
          },
          {
            title: "Статус",
            key: "status",
            sorter: true,
            sortOrder: sortOrder("status"),
            width: 170,
            render: (_, r) => <StatusTag code={r.status_code} name={r.status} />,
          },
          { title: "Terminal ID", dataIndex: "terminal_id", width: 110, render: (v) => v ?? "—" },
          {
            title: "Модель",
            key: "model",
            sorter: true,
            sortOrder: sortOrder("model"),
            width: 190,
            render: (_, r) => (
              <>
                {r.manufacturer} {r.model}
                <div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {r.device_type}
                  </Typography.Text>
                </div>
              </>
            ),
          },
          { title: "Регион", key: "region", dataIndex: "region", sorter: true, sortOrder: sortOrder("region"), width: 170 },
          {
            title: "Адрес",
            width: 280,
            render: (_, r) =>
              r.address ? (
                <>
                  {r.city_district}, {r.address}
                  {r.place_type && (
                    <div>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        {r.place_type}
                        {r.is_24h ? " · круглосуточно" : ""}
                      </Typography.Text>
                    </div>
                  )}
                </>
              ) : (
                <Typography.Text type="secondary">не установлен</Typography.Text>
              ),
          },
          { title: "Филиал", key: "branch", dataIndex: "branch", sorter: true, sortOrder: sortOrder("branch"), width: 190 },
          {
            title: "Валюты",
            width: 100,
            render: (_, r) => (
              <Space size={4} wrap>
                {r.currencies?.split(", ").map((c) => <Tag key={c}>{c}</Tag>)}
                {r.contactless && (
                  <Tooltip title="Бесконтактный ридер">
                    <Tag color="blue">NFC</Tag>
                  </Tooltip>
                )}
              </Space>
            ),
          },
          {
            title: "Ввод",
            key: "commissioning_date",
            dataIndex: "commissioning_date",
            sorter: true,
            sortOrder: sortOrder("commissioning_date"),
            width: 110,
            render: fmt,
          },
          {
            title: "Гарантия до",
            key: "warranty_until",
            dataIndex: "warranty_until",
            sorter: true,
            sortOrder: sortOrder("warranty_until"),
            width: 120,
            render: (d: string | null) => {
              if (!d) return "—";
              const left = dayjs(d).diff(dayjs(), "day");
              return <span style={{ color: left < 0 ? "#8c8c8c" : left < 90 ? "#d4380d" : undefined }}>{fmt(d)}</span>;
            },
          },
        ]}
      />
      <AtmForm open={creating} onClose={() => setCreating(false)} onSaved={(card) => navigate(`/atms/${card.id}`)} />
    </Card>
  );
}
