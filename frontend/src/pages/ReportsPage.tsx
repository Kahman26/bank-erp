import { DownloadOutlined, WarningOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { App, Button, Card, Col, Row, Statistic, Table, Typography } from "antd";
import dayjs from "dayjs";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { useReference } from "@/api/hooks";
import { STATUS_COLORS } from "@/atms/statusColors";
import { BarList, Columns, StackedBar } from "@/reports/charts";

interface Dashboard {
  totals: Record<string, number>;
  by_status: { code: string; name: string; count: number }[];
  by_region: { region: string; total: number; in_service: number; in_repair: number }[];
  by_model: { model: string; total: number; end_of_support_date: string | null }[];
  vendors: { performer: string; events: number; avg_hours: number | null; total_hours: number | null; open: number; cert_events: number }[];
  repairs_by_month: { month: string; events: number; cert_events: number }[];
  end_of_support: { model: string; end_of_support_date: string; total: number }[];
}

function ExcelButton({ report }: { report: string }) {
  const { message } = App.useApp();
  return (
    <Button
      size="small"
      type="text"
      icon={<DownloadOutlined />}
      onClick={() => api.download(`/reports/${report}.xlsx`, `${report}.xlsx`).catch((e) => message.error(e.message))}
    >
      Excel
    </Button>
  );
}

function Tile(props: { title: string; value?: number; suffix?: ReactNode; risk?: boolean; onClick?: () => void }) {
  const alert = props.risk && !!props.value;
  return (
    <Card size="small" hoverable={!!props.onClick} onClick={props.onClick} style={{ height: "100%" }}>
      <Statistic
        groupSeparator=" "
        title={props.title}
        value={props.value ?? "…"}
        suffix={props.suffix}
        prefix={alert ? <WarningOutlined style={{ color: "#d4380d", fontSize: 18 }} /> : undefined}
      />
    </Card>
  );
}

export default function ReportsPage() {
  const navigate = useNavigate();
  const { data: ref } = useReference();
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<Dashboard>("/reports/dashboard") });
  const t = data?.totals ?? {};
  const statusId = (code: string) => ref?.dicts.atm_status.find((s) => s.code === code)?.id;
  const toAtms = (q: string) => () => navigate(`/atms?${q}`);
  const share = (n?: number) => (t.in_network && n !== undefined ? ` · ${Math.round((n / t.in_network) * 100)}%` : "");
  const tile = { xs: 12, md: 8, xl: 4 };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card title="Отчёты" loading={isLoading} styles={{ body: { paddingBottom: 8 } }}>
        <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
          Данные на {dayjs().format("DD.MM.YYYY")}. Плитки открывают список с нужным фильтром, каждая таблица выгружается в Excel.
        </Typography.Paragraph>
        <Row gutter={[12, 12]}>
          <Col {...tile}>
            <Tile title="Банкоматов в сети" value={t.in_network} onClick={toAtms("has_location=true")} />
          </Col>
          <Col {...tile}>
            <Tile
              title={`В эксплуатации${share(t.in_service)}`}
              value={t.in_service}
              onClick={toAtms(`status_id=${statusId("in_service")}`)}
            />
          </Col>
          <Col {...tile}>
            <Tile
              title="В ремонте"
              value={t.in_repair}
              risk
              onClick={toAtms(`status_id=${statusId("repair")}&status_id=${statusId("vendor_repair")}`)}
            />
          </Col>
          <Col {...tile}>
            <Tile title="Не установлены" value={t.not_placed} onClick={toAtms("has_location=false")} />
          </Col>
          <Col {...tile}>
            <Tile title="Гарантия истекает ≤ 90 дн." value={t.warranty_expiring_90} risk onClick={toAtms("warranty_expiring_days=90")} />
          </Col>
          <Col {...tile}>
            <Tile title="Поддержка модели заканчивается ≤ 1 года" value={t.end_of_support_365} risk />
          </Col>
          <Col {...tile}>
            <Tile title="Сертификаты: требуют проверки" value={t.certs_needs_review} risk onClick={() => navigate("/certificates?needs_review=true")} />
          </Col>
          <Col {...tile}>
            <Tile title="Сертификаты истекли" value={t.certs_expired} risk onClick={() => navigate("/certificates?status=expired")} />
          </Col>
          <Col {...tile}>
            <Tile title="Сертификаты истекают ≤ 90 дн." value={t.certs_expiring} risk onClick={() => navigate("/certificates?status=expiring")} />
          </Col>
          <Col {...tile}>
            <Tile title="Узлы без сертификата" value={t.modules_without_cert} risk onClick={() => navigate("/certificates?tab=without")} />
          </Col>
        </Row>
      </Card>

      {data && (
        <>
          <Card title="Статусы банкоматов" size="small">
            <StackedBar
              segments={data.by_status.map((s) => ({ key: s.code, label: s.name, value: s.count, color: STATUS_COLORS[s.code] ?? "#8C8C8C" }))}
            />
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <Card title="Банкоматы в сети по регионам" size="small" extra={<ExcelButton report="by-region" />} style={{ height: "100%" }}>
                <BarList
                  items={data.by_region.map((r) => ({
                    key: r.region,
                    label: r.region,
                    value: r.total,
                    tooltip: `${r.region}: в эксплуатации ${r.in_service}, в ремонте ${r.in_repair}`,
                  }))}
                />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card title="Банкоматы в сети по моделям" size="small" extra={<ExcelButton report="by-model" />} style={{ height: "100%" }}>
                <BarList
                  items={data.by_model.map((m) => ({
                    key: m.model,
                    label: m.model,
                    value: m.total,
                    tooltip: m.end_of_support_date ? `Поддержка производителя до ${dayjs(m.end_of_support_date).format("DD.MM.YYYY")}` : undefined,
                  }))}
                />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card title="Ремонты по месяцам" size="small" extra={<ExcelButton report="repairs-by-month" />} style={{ height: "100%" }}>
                <Columns
                  items={data.repairs_by_month.map((m) => ({
                    key: m.month,
                    label: dayjs(`${m.month}-01`).format("MMM"),
                    value: m.events,
                    tooltip: `${dayjs(`${m.month}-01`).format("MMMM YYYY")}: ремонтов ${m.events}, из них влияли на сертификацию ${m.cert_events}`,
                  }))}
                />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card title="Ремонты и простои за 12 месяцев" size="small" extra={<ExcelButton report="vendors" />} style={{ height: "100%" }}>
                <Table
                  rowKey="performer"
                  size="small"
                  pagination={false}
                  dataSource={data.vendors}
                  columns={[
                    { title: "Исполнитель", dataIndex: "performer" },
                    { title: "Ремонтов", dataIndex: "events", align: "right" },
                    { title: "Средний простой, ч", dataIndex: "avg_hours", align: "right", render: (v) => v ?? "—" },
                    { title: "Открыто", dataIndex: "open", align: "right" },
                  ]}
                />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card title="Окончание поддержки моделей (2 года)" size="small" extra={<ExcelButton report="end-of-support" />} style={{ height: "100%" }}>
                <Table
                  rowKey="model"
                  size="small"
                  pagination={false}
                  dataSource={data.end_of_support}
                  locale={{ emptyText: "Нет моделей с окончанием поддержки в ближайшие 2 года" }}
                  columns={[
                    { title: "Модель", dataIndex: "model" },
                    {
                      title: "Поддержка до",
                      dataIndex: "end_of_support_date",
                      render: (v: string) => (
                        <span style={{ color: dayjs(v).isBefore(dayjs().add(1, "year")) ? "#cf1322" : undefined }}>{dayjs(v).format("DD.MM.YYYY")}</span>
                      ),
                    },
                    { title: "Банкоматов", dataIndex: "total", align: "right" },
                  ]}
                />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card title="Гарантия истекает в ближайшие 90 дней" size="small" extra={<ExcelButton report="warranty" />} style={{ height: "100%" }}>
                <Typography.Paragraph>
                  Банкоматов: <b>{t.warranty_expiring_90}</b>. После окончания гарантии ремонт оплачивает банк — заранее
                  продлите сервисный договор.
                </Typography.Paragraph>
                <Button onClick={toAtms("warranty_expiring_days=90&sort=warranty_until")}>Открыть список</Button>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}
