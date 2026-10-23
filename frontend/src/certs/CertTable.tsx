import { DownloadOutlined, EditOutlined, MoreOutlined, UploadOutlined, WarningOutlined } from "@ant-design/icons";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { App, Button, Dropdown, Space, Table, Tag, Tooltip, Typography, Upload } from "antd";
import dayjs from "dayjs";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

import CertForm from "./CertForm";
import { CERT_STATUS, type CertPage, type CertRow } from "./types";

const d = (v: string | null) => (v ? dayjs(v).format("DD.MM.YYYY") : "—");

/** Таблица сертификатов по параметрам запроса. Используется в реестре и в карточке банкомата. */
export default function CertTable({ query, atmId, compact }: { query: string; atmId?: number; compact?: boolean }) {
  const { can } = useAuth();
  const qc = useQueryClient();
  const { message } = App.useApp();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [editing, setEditing] = useState<CertRow | null>(null);
  const q = `${query}${query ? "&" : ""}page=${page}&page_size=${pageSize}`;
  const { data, isFetching } = useQuery({
    queryKey: ["certificates", q],
    queryFn: () => api.get<CertPage>(`/certificates?${q}`),
    placeholderData: keepPreviousData,
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["certificates"] });
    qc.invalidateQueries({ queryKey: ["cert-summary"] });
    qc.invalidateQueries({ queryKey: ["atm"] });
  };
  const patch = async (row: CertRow, body: Record<string, unknown>, ok: string) => {
    try {
      await api.patch(`/certificates/${row.id}`, body);
      message.success(ok);
      refresh();
    } catch (e) {
      message.error((e as Error).message);
    }
  };
  const upload = async (row: CertRow, file: File) => {
    const form = new FormData();
    form.append("file", file);
    try {
      await api.upload(`/certificates/${row.id}/document`, form);
      message.success("Скан загружен");
      refresh();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <>
      <Table<CertRow>
        rowKey="id"
        size="small"
        loading={isFetching}
        dataSource={data?.items}
        scroll={{ x: compact ? 900 : 1250 }}
        pagination={{
          current: page,
          pageSize,
          total: data?.total,
          showSizeChanger: !compact,
          hideOnSinglePage: true,
          onChange: (p, s) => {
            setPage(p);
            setPageSize(s);
          },
        }}
        columns={[
          {
            title: "Объект",
            width: 230,
            render: (_, r) =>
              r.object === "model" ? (
                <>
                  Модель {r.model}
                  <div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      банкоматов: {r.atm_count}
                    </Typography.Text>
                  </div>
                </>
              ) : (
                <>
                  {!atmId && r.atm_id ? <Link to={`/atms/${r.atm_id}`}>{r.atm_code}</Link> : r.object === "atm" ? "Банкомат" : null}
                  {r.module_type && (
                    <div style={{ fontSize: 12 }}>
                      {r.module_type} · {r.module_serial}
                      {r.module_removed_at && <Tag style={{ marginLeft: 4 }}>снят</Tag>}
                    </div>
                  )}
                </>
              ),
          },
          { title: "Вид", dataIndex: "cert_type", width: 190 },
          { title: "ПС", dataIndex: "payment_scheme", width: 100, render: (v) => v ?? "—" },
          { title: "Номер", dataIndex: "cert_number", width: 150 },
          { title: "Выдан", dataIndex: "issued_at", width: 100, render: d, responsive: ["lg"] },
          {
            title: "Действует до",
            dataIndex: "valid_until",
            width: 120,
            render: (v: string, r) => {
              const left = dayjs(v).diff(dayjs(), "day");
              return (
                <Tooltip title={r.status === "expiring" ? `осталось ${left} дн.` : undefined}>
                  <span>{d(v)}</span>
                </Tooltip>
              );
            },
          },
          {
            title: "Статус",
            width: 170,
            render: (_, r) => (
              <Space size={4} wrap>
                <Tag color={CERT_STATUS[r.status].color}>{CERT_STATUS[r.status].label}</Tag>
                {r.needs_review && (
                  <Tooltip title="Узел заменён — сертификат нужно проверить">
                    <Tag color="red" icon={<WarningOutlined />}>
                      проверить
                    </Tag>
                  </Tooltip>
                )}
              </Space>
            ),
          },
          { title: "Кем предоставлен", dataIndex: "source", width: 160, render: (v) => v ?? "—", responsive: ["xl"] },
          {
            title: "Скан",
            width: 70,
            render: (_, r) =>
              r.has_document ? (
                <Button
                  size="small"
                  type="text"
                  icon={<DownloadOutlined />}
                  onClick={() => api.download(`/certificates/${r.id}/document`, `certificate-${r.cert_number}`).catch((e) => message.error(e.message))}
                />
              ) : (
                <Typography.Text type="secondary">нет</Typography.Text>
              ),
          },
          ...(can("edit")
            ? [
                {
                  width: 50,
                  render: (_: unknown, r: CertRow) => (
                    <Dropdown
                      trigger={["click"]}
                      menu={{
                        items: [
                          { key: "edit", icon: <EditOutlined />, label: "Изменить", onClick: () => setEditing(r) },
                          {
                            key: "doc",
                            icon: <UploadOutlined />,
                            label: (
                              <Upload accept=".pdf,.jpg,.jpeg,.png" showUploadList={false} beforeUpload={(f) => (upload(r, f), false)}>
                                {r.has_document ? "Заменить скан" : "Загрузить скан"}
                              </Upload>
                            ),
                          },
                          ...(r.needs_review
                            ? [{ key: "reviewed", label: "Отметить проверенным", onClick: () => patch(r, { needs_review: false }, "Отмечено") }]
                            : []),
                          { type: "divider" as const },
                          r.manual_status === "renewal"
                            ? { key: "unrenew", label: "Снять «На продлении»", onClick: () => patch(r, { manual_status: "" }, "Готово") }
                            : { key: "renew", label: "На продлении", onClick: () => patch(r, { manual_status: "renewal" }, "Готово") },
                          r.manual_status === "revoked"
                            ? { key: "unrevoke", label: "Снять «Отозван»", onClick: () => patch(r, { manual_status: "" }, "Готово") }
                            : { key: "revoke", label: "Отозван", danger: true, onClick: () => patch(r, { manual_status: "revoked" }, "Готово") },
                        ],
                      }}
                    >
                      <Button size="small" type="text" icon={<MoreOutlined />} />
                    </Dropdown>
                  ),
                },
              ]
            : []),
        ]}
      />
      <CertForm open={editing !== null} cert={editing ?? undefined} onClose={() => setEditing(null)} onSaved={refresh} />
    </>
  );
}
