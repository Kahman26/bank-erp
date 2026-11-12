import { DownloadOutlined, PlusOutlined } from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Card, Col, Input, Row, Select, Space, Statistic, Table, Tabs } from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { useReference } from "@/api/hooks";
import CertForm from "@/certs/CertForm";
import CertTable from "@/certs/CertTable";
import { CERT_STATUS, type CertStatus, type CertSummary, type WithoutCertRow } from "@/certs/types";
import { useAuth } from "@/auth/AuthContext";
import { brand } from "@/theme/brand";
import PagePanel from "@/components/PagePanel";

const TILES: { key: CertStatus | "needs_review"; title: string; color?: string }[] = [
  { key: "needs_review", title: "Требуют проверки", color: brand.error },
  { key: "expired", title: "Истекли", color: brand.error },
  { key: "expiring", title: "Истекают ≤ 90 дн.", color: brand.warning },
  { key: "renewal", title: "На продлении", color: brand.info },
  { key: "valid", title: "Действуют", color: brand.greenHover },
  { key: "revoked", title: "Отозваны" },
];

export default function CertificatesPage() {
  const { can } = useAuth();
  const { data: ref } = useReference();
  const qc = useQueryClient();
  const { message } = App.useApp();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const tab = params.get("tab") ?? "registry";
  const { data: summary } = useQuery({ queryKey: ["cert-summary"], queryFn: () => api.get<CertSummary>("/certificates/summary") });
  const { data: without = [], isLoading: withoutLoading } = useQuery({
    queryKey: ["certificates", "without"],
    queryFn: () => api.get<WithoutCertRow[]>("/certificates/modules-without"),
    enabled: tab === "without",
  });

  const set = (key: string, value: string | string[] | undefined) => {
    const next = new URLSearchParams(params);
    next.delete(key);
    for (const v of Array.isArray(value) ? value : value ? [value] : []) next.append(key, v);
    setParams(next, { replace: true });
  };
  const query = new URLSearchParams(params);
  query.delete("tab");

  const pickTile = (key: CertStatus | "needs_review") => {
    const next = new URLSearchParams();
    if (key === "needs_review") next.set("needs_review", "true");
    else next.set("status", key);
    setParams(next, { replace: true });
  };

  return (
    <PagePanel
      title="Сертификаты"
      description="Сертификация оборудования и контроль сроков действия"
      extra={
        <Space wrap>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => api.download(`/certificates/export.xlsx?${query}`, "certificates.xlsx").catch((e) => message.error(e.message))}
          >
            Excel
          </Button>
          {can("edit") && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>
              Добавить
            </Button>
          )}
        </Space>
      }
    >
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {TILES.map((t) => (
          <Col xs={12} sm={8} lg={4} key={t.key}>
            <Card
              className={"cert-summary-card" + ((t.key === "needs_review" ? params.get("needs_review") === "true" : params.getAll("status").includes(t.key)) ? " is-selected" : "")}
              size="small" hoverable onClick={() => pickTile(t.key)}
              role="link" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") pickTile(t.key); }}
            >
              <Statistic groupSeparator=" " title={t.title} value={summary?.[t.key] ?? "…"} valueStyle={{ color: summary?.[t.key] ? t.color : undefined }} />
            </Card>
          </Col>
        ))}
      </Row>
      <Tabs
        activeKey={tab}
        onChange={(k) => set("tab", k === "registry" ? undefined : k)}
        items={[
          {
            key: "registry",
            label: "Реестр",
            children: (
              <>
                <Space wrap style={{ marginBottom: 12 }}>
                  <Input.Search
                    allowClear
                    placeholder="Номер, код банкомата, серийный № узла, модель"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onSearch={(v) => set("q", v.trim() || undefined)}
                    style={{ width: 340 }}
                  />
                  <Select
                    mode="multiple"
                    allowClear
                    placeholder="Статус"
                    style={{ minWidth: 180 }}
                    value={params.getAll("status")}
                    onChange={(v: string[]) => set("status", v)}
                    options={Object.entries(CERT_STATUS).map(([value, s]) => ({ value, label: s.label }))}
                  />
                  <Select
                    mode="multiple"
                    allowClear
                    placeholder="Вид"
                    style={{ minWidth: 200 }}
                    value={params.getAll("cert_type_id")}
                    onChange={(v: string[]) => set("cert_type_id", v)}
                    options={ref?.dicts.cert_type.map((t) => ({ value: String(t.id), label: t.name }))}
                  />
                  <Select
                    mode="multiple"
                    allowClear
                    placeholder="Платёжная система"
                    style={{ minWidth: 180 }}
                    value={params.getAll("payment_scheme_id")}
                    onChange={(v: string[]) => set("payment_scheme_id", v)}
                    options={ref?.payment_schemes.map((s) => ({ value: String(s.id), label: s.name }))}
                  />
                  <Select
                    mode="multiple"
                    allowClear
                    placeholder="На что выдан"
                    style={{ minWidth: 160 }}
                    value={params.getAll("object")}
                    onChange={(v: string[]) => set("object", v)}
                    options={[
                      { value: "model", label: "Модель" },
                      { value: "atm", label: "Банкомат" },
                      { value: "module", label: "Узел" },
                    ]}
                  />
                  <Select
                    allowClear
                    placeholder="Требуют проверки"
                    style={{ minWidth: 170 }}
                    value={params.get("needs_review") ?? undefined}
                    onChange={(v?: string) => set("needs_review", v)}
                    options={[{ value: "true", label: "Только требующие проверки" }]}
                  />
                </Space>
                <CertTable query={query.toString()} />
              </>
            ),
          },
          {
            key: "without",
            label: `Узлы без сертификата${summary ? ` (${summary.modules_without})` : ""}`,
            children: (
              <Table<WithoutCertRow>
                rowKey="id"
                size="small"
                loading={withoutLoading}
                dataSource={without}
                pagination={{ pageSize: 50, hideOnSinglePage: true }}
                scroll={{ x: 700 }}
                columns={[
                  { title: "Банкомат", dataIndex: "atm_code", render: (v, r) => <Link to={`/atms/${r.atm_id}`}>{v}</Link> },
                  { title: "Модель", dataIndex: "model" },
                  { title: "Узел", dataIndex: "module_type" },
                  { title: "Серийный №", dataIndex: "serial_number" },
                  { title: "Установлен", dataIndex: "installed_at", render: (v) => dayjs(v).format("DD.MM.YYYY") },
                ]}
              />
            ),
          },
        ]}
      />
      <CertForm
        open={creating}
        onClose={() => setCreating(false)}
        onSaved={() => {
          qc.invalidateQueries({ queryKey: ["certificates"] });
          qc.invalidateQueries({ queryKey: ["cert-summary"] });
        }}
      />
    </PagePanel>
  );
}
