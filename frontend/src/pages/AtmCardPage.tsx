import { ArrowLeftOutlined, EditOutlined, WarningOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Modal,
  Result,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Timeline,
  Tooltip,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { useApiMutation, useReference } from "@/api/hooks";
import AtmForm from "@/atms/AtmForm";
import AtmMap from "@/atms/AtmMap";
import { StatusTag } from "@/atms/status";
import type { AtmCard, Certificate, LocationInfo, Processing } from "@/atms/types";
import { useAuth } from "@/auth/AuthContext";

const d = (v: string | null | undefined) => (v ? dayjs(v).format("DD.MM.YYYY") : "—");
const dt = (v: string | null | undefined) => (v ? dayjs(v).format("DD.MM.YYYY HH:mm") : "—");
const yes = (v: unknown) => (v === null || v === undefined ? "—" : v ? "да" : "нет");

const CERT_COLORS: Record<Certificate["status"], string> = {
  valid: "green",
  expiring: "orange",
  expired: "red",
  renewal: "blue",
  revoked: "default",
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card size="small" title={title} style={{ marginBottom: 16 }}>
      {children}
    </Card>
  );
}

function LocationBlock({ loc }: { loc: LocationInfo }) {
  return (
    <Descriptions column={1} size="small">
      <Descriptions.Item label="Точка">{loc.name}</Descriptions.Item>
      <Descriptions.Item label="Адрес">
        {loc.region}, {loc.city_district}, {loc.address}
      </Descriptions.Item>
      {loc.landmark && <Descriptions.Item label="Ориентир">{loc.landmark}</Descriptions.Item>}
      <Descriptions.Item label="Тип места">
        {loc.place_type} · {loc.indoor ? "в помещении" : "на улице"}
      </Descriptions.Item>
      <Descriptions.Item label="Режим работы">{loc.working_hours}</Descriptions.Item>
      <Descriptions.Item label="Координаты">
        {loc.latitude.toFixed(6)}, {loc.longitude.toFixed(6)}
      </Descriptions.Item>
      {loc.site_contact && <Descriptions.Item label="Контакт на объекте">{loc.site_contact}</Descriptions.Item>}
      {loc.premises_owner && <Descriptions.Item label="Владелец помещения">{loc.premises_owner}</Descriptions.Item>}
    </Descriptions>
  );
}

function ProcessingsModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm<{ items: Partial<Processing>[] }>();
  const save = useApiMutation((items: Partial<Processing>[]) => api.put(`/atms/${card.id}/processings`, items), {
    success: "Процессинги сохранены",
    invalidate: [["atm", card.id], ["atms"]],
  });
  const opts = (kind: string) => (ref?.dicts[kind] ?? []).map((x) => ({ value: x.id, label: x.name }));

  return (
    <Modal
      title="Подключение к процессингам"
      open={open}
      width={Math.min(900, window.innerWidth)}
      onCancel={onClose}
      okText="Сохранить"
      afterOpenChange={(o) => o && form.setFieldsValue({ items: card.processings })}
      onOk={async () => {
        const { items } = await form.validateFields();
        await save.mutateAsync(items ?? []);
        onClose();
      }}
      destroyOnClose
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.List name="items">
          {(fields, { add, remove }) => (
            <>
              {fields.map((f) => (
                <Row gutter={8} key={f.key} align="bottom">
                  <Col xs={24} sm={6}>
                    <Form.Item name={[f.name, "processing_id"]} label="Процессинг" rules={[{ required: true }]}>
                      <Select options={ref?.processings.map((p) => ({ value: p.id, label: p.name }))} />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={4}>
                    <Form.Item name={[f.name, "terminal_id"]} label="Terminal ID" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={4}>
                    <Form.Item name={[f.name, "merchant_id"]} label="Merchant ID" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={3}>
                    <Form.Item name={[f.name, "host_protocol_id"]} label="Протокол">
                      <Select allowClear options={opts("host_protocol")} />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={3}>
                    <Form.Item name={[f.name, "connection_type_id"]} label="Канал">
                      <Select allowClear options={opts("connection_type")} />
                    </Form.Item>
                  </Col>
                  <Col xs={18} sm={3}>
                    <Form.Item name={[f.name, "ip_address"]} label="IP">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={6} sm={1}>
                    <Form.Item>
                      <Button danger type="text" onClick={() => remove(f.name)}>
                        ✕
                      </Button>
                    </Form.Item>
                  </Col>
                </Row>
              ))}
              <Button onClick={() => add()} disabled={fields.length >= (ref?.processings.length ?? 3)}>
                Добавить процессинг
              </Button>
            </>
          )}
        </Form.List>
      </Form>
    </Modal>
  );
}

export default function AtmCardPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const { data: ref } = useReference();
  const [editOpen, setEditOpen] = useState(false);
  const [procOpen, setProcOpen] = useState(false);
  const { data: card, error, isLoading } = useQuery({
    queryKey: ["atm", Number(id)],
    queryFn: () => api.get<AtmCard>(`/atms/${id}`),
  });

  if (isLoading) return <Card loading />;
  if (error || !card)
    return (
      <Result
        status={(error as ApiError)?.status === 404 ? "404" : "error"}
        title={(error as Error)?.message ?? "Не удалось загрузить"}
        extra={<Button onClick={() => navigate("/atms")}>К списку</Button>}
      />
    );

  const statusNames = Object.fromEntries((ref?.dicts.atm_status ?? []).map((x) => [x.code, x.name]));
  const certIssues = card.certificates.filter((c) => c.needs_review || c.status === "expired" || c.status === "expiring");
  const openRepair = card.service_events.find((e) => !e.finished_at);
  const installed = card.modules.filter((m) => !m.removed_at);
  const removed = card.modules.filter((m) => m.removed_at);
  const c = card.config;

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          Назад
        </Button>
      </Space>
      <Card
        title={
          <Space wrap>
            <span style={{ fontSize: 20 }}>{card.atm_code}</span>
            <StatusTag code={card.header.status_code} name={card.header.status} />
          </Space>
        }
        extra={
          can("edit") && (
            <Button icon={<EditOutlined />} onClick={() => setEditOpen(true)}>
              Изменить
            </Button>
          )
        }
      >
        <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
          <Link to={`/models`}>{card.header.model}</Link> · {card.header.device_type}
          {card.header.address && ` · ${card.header.address}`}
        </Typography.Paragraph>

        {openRepair && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message={`Открыт ремонт с ${dt(openRepair.started_at)}: ${openRepair.problem}`}
            description={`Исполнитель: ${openRepair.performer}${openRepair.ticket_number ? `, заявка ${openRepair.ticket_number}` : ""}`}
          />
        )}
        {certIssues.length > 0 && (
          <Alert
            type="error"
            showIcon
            icon={<WarningOutlined />}
            style={{ marginBottom: 12 }}
            message={`Сертификаты требуют внимания: ${certIssues.length}`}
            description={certIssues
              .slice(0, 4)
              .map((x) => `${x.cert_type}${x.payment_scheme ? ` ${x.payment_scheme}` : ""} — ${x.needs_review ? "проверить после замены узла" : x.status_label.toLowerCase()} (${d(x.valid_until)})`)
              .join("; ")}
          />
        )}

        <Tabs
          items={[
            {
              key: "main",
              label: "Основное",
              children: (
                <Row gutter={16}>
                  <Col xs={24} lg={12}>
                    <Section title="Банкомат">
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="Серийный номер">{card.main.serial_number}</Descriptions.Item>
                        <Descriptions.Item label="Инвентарный номер">{card.main.inventory_number ?? "—"}</Descriptions.Item>
                        <Descriptions.Item label="Формат установки">{card.main.install_format}</Descriptions.Item>
                        <Descriptions.Item label="Филиал">{card.main.branch}</Descriptions.Item>
                        <Descriptions.Item label="Покупка">{d(card.main.purchase_date)}</Descriptions.Item>
                        <Descriptions.Item label="Ввод в эксплуатацию">{d(card.main.commissioning_date)}</Descriptions.Item>
                        {card.main.decommission_date && (
                          <Descriptions.Item label="Вывод из эксплуатации">{d(card.main.decommission_date)}</Descriptions.Item>
                        )}
                        <Descriptions.Item label="Валюты">{card.main.currencies.join(", ")}</Descriptions.Item>
                        <Descriptions.Item label="Принимаемые карты">{card.main.schemes.join(", ") || "—"}</Descriptions.Item>
                        <Descriptions.Item label="Функции">{card.main.services.join(", ") || "—"}</Descriptions.Item>
                        <Descriptions.Item label="Поддержка модели до">{d(card.main.end_of_support_date)}</Descriptions.Item>
                        {card.main.notes && <Descriptions.Item label="Примечание">{card.main.notes}</Descriptions.Item>}
                      </Descriptions>
                    </Section>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Section title="Место установки">
                      {card.location ? (
                        <>
                          <LocationBlock loc={card.location} />
                          <div style={{ marginTop: 12 }}>
                            <AtmMap
                              height={240}
                              popupExtra={false}
                              statusNames={statusNames}
                              points={[[card.id, card.atm_code, card.location.latitude, card.location.longitude, card.header.status_code]]}
                            />
                          </div>
                        </>
                      ) : (
                        <Empty description="Банкомат сейчас не установлен" />
                      )}
                    </Section>
                  </Col>
                </Row>
              ),
            },
            {
              key: "config",
              label: "Комплектация и узлы",
              children: (
                <>
                  <Section title="Комплектация">
                    <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }}>
                      <Descriptions.Item label="Экран">
                        {c.screen_size_in ? `${c.screen_size_in}"` : "—"} {c.screen_resolution ?? ""} {c.screen_orientation ? `· ${c.screen_orientation}` : ""}
                      </Descriptions.Item>
                      <Descriptions.Item label="Способ ввода">{c.input_method ?? "—"}</Descriptions.Item>
                      <Descriptions.Item label="Кассет">{c.cassette_count ?? "—"}</Descriptions.Item>
                      <Descriptions.Item label="Сейф">
                        {c.safe_class ?? "—"} {c.safe_lock ? `· ${c.safe_lock}` : ""}
                      </Descriptions.Item>
                      <Descriptions.Item label="Доступ для обслуживания">{c.service_access ?? "—"}</Descriptions.Item>
                      <Descriptions.Item label="NFC">{yes(c.contactless)}</Descriptions.Item>
                      <Descriptions.Item label="Экран для улицы">{yes(c.screen_sunlight)}</Descriptions.Item>
                      <Descriptions.Item label="Фильтр конфиденциальности">{yes(c.privacy_filter)}</Descriptions.Item>
                      <Descriptions.Item label="Аудиоразъём">{yes(c.audio_jack)}</Descriptions.Item>
                      <Descriptions.Item label="ИБП">{yes(c.ups)}</Descriptions.Item>
                    </Descriptions>
                  </Section>
                  <Section title={`Установленные узлы (${installed.length})`}>
                    <Table
                      rowKey="id"
                      size="small"
                      pagination={false}
                      scroll={{ x: 800 }}
                      dataSource={installed}
                      columns={[
                        {
                          title: "Узел",
                          render: (_, m) => (
                            <>
                              {m.type} {m.xfs && <Tag>{m.xfs}</Tag>}
                            </>
                          ),
                        },
                        { title: "Модель", render: (_, m) => [m.vendor, m.model].filter(Boolean).join(" ") || "—" },
                        { title: "Серийный №", dataIndex: "serial_number" },
                        { title: "Прошивка", dataIndex: "firmware_version", render: (v) => v ?? "—" },
                        { title: "Установлен", dataIndex: "installed_at", render: d },
                        {
                          title: "Параметры",
                          render: (_, m) =>
                            Object.entries(m.attributes)
                              .map(([k, v]) => `${k}: ${v}`)
                              .join("; ") || "—",
                        },
                      ]}
                    />
                  </Section>
                  {removed.length > 0 && (
                    <Section title={`Снятые узлы (${removed.length})`}>
                      <Table
                        rowKey="id"
                        size="small"
                        pagination={false}
                        dataSource={removed}
                        columns={[
                          { title: "Узел", dataIndex: "type" },
                          { title: "Серийный №", dataIndex: "serial_number" },
                          { title: "Установлен", dataIndex: "installed_at", render: d },
                          { title: "Снят", dataIndex: "removed_at", render: d },
                          { title: "", render: (_, m) => m.is_faulty && <Tag color="red">неисправен</Tag> },
                        ]}
                      />
                    </Section>
                  )}
                </>
              ),
            },
            {
              key: "software",
              label: "ПО",
              children: (
                <Table
                  rowKey="id"
                  size="small"
                  pagination={false}
                  dataSource={card.software}
                  columns={[
                    { title: "Тип", dataIndex: "type" },
                    { title: "Название", dataIndex: "name" },
                    { title: "Версия", dataIndex: "version" },
                    { title: "Установлено", dataIndex: "installed_at", render: d },
                  ]}
                />
              ),
            },
            {
              key: "processing",
              label: "Процессинги",
              children: (
                <>
                  {can("edit") && (
                    <Button style={{ marginBottom: 12 }} onClick={() => setProcOpen(true)}>
                      Изменить подключения
                    </Button>
                  )}
                  <Table
                    rowKey="id"
                    size="small"
                    pagination={false}
                    dataSource={card.processings}
                    locale={{ emptyText: "Банкомат не зарегистрирован в процессингах" }}
                    columns={[
                      { title: "Процессинг", dataIndex: "processing" },
                      { title: "Terminal ID", dataIndex: "terminal_id", render: (v) => <b>{v}</b> },
                      { title: "Merchant ID", dataIndex: "merchant_id" },
                      { title: "Протокол", dataIndex: "host_protocol", render: (v) => v ?? "—" },
                      { title: "Канал связи", dataIndex: "connection_type", render: (v) => v ?? "—" },
                      ...(can("edit") ? [{ title: "IP", dataIndex: "ip_address", render: (v: string | null) => v ?? "—" }] : []),
                    ]}
                  />
                  <ProcessingsModal card={card} open={procOpen} onClose={() => setProcOpen(false)} />
                </>
              ),
            },
            {
              key: "placements",
              label: `Размещения (${card.placements.length})`,
              children: card.placements.length ? (
                <Timeline
                  items={card.placements.map((p) => ({
                    color: p.placed_to ? "gray" : "green",
                    children: (
                      <>
                        <b>
                          {d(p.placed_from)} — {p.placed_to ? d(p.placed_to) : "сейчас"}
                        </b>
                        {p.move_reason && <Tag style={{ marginLeft: 8 }}>{p.move_reason}</Tag>}
                        <div>
                          {p.location.name}, {p.location.city_district}, {p.location.address}
                        </div>
                        {p.basis_document && <Typography.Text type="secondary">Основание: {p.basis_document}</Typography.Text>}
                      </>
                    ),
                  }))}
                />
              ) : (
                <Empty description="Банкомат ещё не устанавливался" />
              ),
            },
            {
              key: "repairs",
              label: `Ремонты (${card.service_events.length})`,
              children: (
                <Table
                  rowKey="id"
                  size="small"
                  scroll={{ x: 1000 }}
                  dataSource={card.service_events}
                  pagination={{ pageSize: 20, hideOnSinglePage: true }}
                  columns={[
                    { title: "Начало", dataIndex: "started_at", render: dt, width: 140 },
                    { title: "Тип", dataIndex: "type", width: 140 },
                    {
                      title: "Неисправность / работы",
                      render: (_, e) => (
                        <>
                          {e.problem}
                          {e.work_done && <div style={{ color: "#595959" }}>{e.work_done}</div>}
                          {e.replacements.map((r) => (
                            <div key={r.removed} style={{ fontSize: 12 }}>
                              {r.removed} → {r.installed}
                            </div>
                          ))}
                        </>
                      ),
                    },
                    {
                      title: "Простой, ч",
                      dataIndex: "downtime_hours",
                      width: 100,
                      render: (v: number | null) => (v === null ? <Tag color="orange">открыт</Tag> : v),
                    },
                    { title: "Исполнитель", dataIndex: "performer", width: 150 },
                    { title: "Заявка", dataIndex: "ticket_number", width: 150, render: (v) => v ?? "—" },
                    {
                      title: "",
                      width: 40,
                      render: (_, e) =>
                        e.affects_certification && (
                          <Tooltip title="Влияет на сертификацию">
                            <WarningOutlined style={{ color: "#d4380d" }} />
                          </Tooltip>
                        ),
                    },
                  ]}
                />
              ),
            },
            {
              key: "certs",
              label: `Сертификаты (${card.certificates.length})`,
              children: (
                <Table<Certificate>
                  rowKey="id"
                  size="small"
                  scroll={{ x: 900 }}
                  pagination={false}
                  dataSource={card.certificates}
                  columns={[
                    { title: "Объект", dataIndex: "object_label" },
                    { title: "Вид", dataIndex: "cert_type" },
                    { title: "ПС", dataIndex: "payment_scheme", render: (v) => v ?? "—" },
                    { title: "Номер", dataIndex: "cert_number" },
                    { title: "Действует до", dataIndex: "valid_until", render: d },
                    {
                      title: "Статус",
                      render: (_, x) => (
                        <Space size={4}>
                          <Tag color={CERT_COLORS[x.status]}>{x.status_label}</Tag>
                          {x.needs_review && <Tag color="red">проверить</Tag>}
                        </Space>
                      ),
                    },
                    { title: "Кем предоставлен", dataIndex: "source", render: (v) => v ?? "—" },
                  ]}
                />
              ),
            },
            {
              key: "contract",
              label: "Гарантия и договор",
              children: card.contract ? (
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="Окончание гарантийной поддержки">
                    {d(card.contract.warranty_until)}
                    {card.contract.warranty_until && dayjs(card.contract.warranty_until).isBefore(dayjs()) && (
                      <Tag style={{ marginLeft: 8 }}>истекла</Tag>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="Сервисный вендор">{card.contract.service_vendor ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="SLA на ремонт, ч">{card.contract.service_sla_hours ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="Поставщик">{card.contract.supplier ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="Договор поставки">{card.contract.purchase_contract ?? "—"}</Descriptions.Item>
                  <Descriptions.Item label="Стоимость">
                    {card.contract.purchase_price
                      ? `${Number(card.contract.purchase_price).toLocaleString("ru-RU")} ${card.contract.price_currency ?? ""}`
                      : "—"}
                  </Descriptions.Item>
                </Descriptions>
              ) : (
                <Empty description="Данные договора не заполнены" />
              ),
            },
            {
              key: "history",
              label: "История статусов",
              children: (
                <Timeline
                  items={card.status_history.map((h) => ({
                    children: (
                      <>
                        <b>{h.status}</b> · {dt(h.changed_at)}
                        {h.changed_by && ` · ${h.changed_by}`}
                        {h.comment && <div style={{ color: "#595959" }}>{h.comment}</div>}
                      </>
                    ),
                  }))}
                />
              ),
            },
          ]}
        />
      </Card>
      <AtmForm open={editOpen} onClose={() => setEditOpen(false)} card={card} onSaved={() => undefined} />
    </>
  );
}
