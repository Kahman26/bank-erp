import { DownloadOutlined, InboxOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Card,
  Checkbox,
  Col,
  Result,
  Row,
  Segmented,
  Space,
  Statistic,
  Steps,
  Table,
  Tag,
  Typography,
  Upload,
} from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";

interface RowIssue {
  line: number;
  atm_code: string;
  action: "create" | "update" | "error";
  errors: string[];
  warnings: string[];
}

interface Preview {
  total: number;
  create: number;
  update: number;
  errors: number;
  warnings: number;
  rows: RowIssue[];
}

interface CommitResult {
  created: number;
  updated: number;
  unchanged: number;
  skipped: number;
  moved: number;
}

const ACTION: Record<RowIssue["action"], { label: string; color: string }> = {
  create: { label: "новый", color: "green" },
  update: { label: "обновится", color: "blue" },
  error: { label: "ошибка", color: "red" },
};

export default function ImportPage() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [result, setResult] = useState<CommitResult | null>(null);
  const [skipErrors, setSkipErrors] = useState(false);
  const [show, setShow] = useState<"errors" | "warnings">("errors");
  const [busy, setBusy] = useState(false);

  const form = () => {
    const f = new FormData();
    f.append("file", file!);
    return f;
  };

  const check = async () => {
    setBusy(true);
    try {
      const p = await api.upload<Preview>("/import/atms/preview", form());
      setPreview(p);
      setShow(p.errors ? "errors" : "warnings");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    setBusy(true);
    try {
      const f = form();
      f.append("skip_errors", String(skipErrors));
      setResult(await api.upload<CommitResult>("/import/atms/commit", f));
      qc.invalidateQueries({ queryKey: ["atms"] });
      qc.invalidateQueries({ queryKey: ["atm-map"] });
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setSkipErrors(false);
  };

  if (result) {
    return (
      <Card title="Загрузка данных">
        <Result
          status={result.skipped ? "warning" : "success"}
          title="Загрузка завершена"
          subTitle={[
            `создано: ${result.created}`,
            `обновлено: ${result.updated}`,
            `без изменений: ${result.unchanged}`,
            result.moved ? `перемещено: ${result.moved}` : null,
            result.skipped ? `пропущено строк с ошибками: ${result.skipped}` : null,
          ]
            .filter(Boolean)
            .join(" · ")}
          extra={[
            <Button key="list" type="primary" onClick={() => navigate("/atms")}>
              К списку банкоматов
            </Button>,
            <Button key="again" onClick={reset}>
              Загрузить ещё файл
            </Button>,
          ]}
        />
      </Card>
    );
  }

  const shown = (preview?.rows ?? []).filter((r) => (show === "errors" ? r.errors.length : r.warnings.length));
  const canCommit = preview && preview.create + preview.update > 0 && (preview.errors === 0 || skipErrors);

  return (
    <Card
      title="Загрузка данных"
      extra={
        <Button icon={<DownloadOutlined />} onClick={() => api.download("/import/atms/template", "atm-import-template.xlsx").catch((e) => message.error(e.message))}>
          Шаблон Excel
        </Button>
      }
    >
      <Steps
        size="small"
        current={preview ? 2 : file ? 1 : 0}
        style={{ marginBottom: 20 }}
        items={[{ title: "Файл" }, { title: "Проверка" }, { title: "Загрузка" }]}
      />
      <Typography.Paragraph type="secondary">
        CSV или Excel в формате шаблона: колонки можно называть кодами (<code>atm_code</code>) или русскими названиями из
        листа «Описание». Банкомат ищется по коду: новые создаются, существующие обновляются. Если координаты изменились —
        банкомат считается перемещённым, история размещений сохраняется. Повторная загрузка того же файла ничего не меняет.
      </Typography.Paragraph>

      <Upload.Dragger
        accept=".csv,.xlsx"
        maxCount={1}
        beforeUpload={(f) => {
          setFile(f);
          setPreview(null);
          return false;
        }}
        onRemove={reset}
        fileList={file ? [{ uid: "1", name: file.name, status: "done" }] : []}
        style={{ marginBottom: 16 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">Перетащите файл сюда или нажмите, чтобы выбрать</p>
        <p className="ant-upload-hint">.csv или .xlsx, до 5 МБ и 5 000 строк</p>
      </Upload.Dragger>

      {file && !preview && (
        <Button type="primary" onClick={check} loading={busy}>
          Проверить файл
        </Button>
      )}

      {preview && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {(
              [
                ["Строк в файле", preview.total, undefined],
                ["Новых банкоматов", preview.create, "#389e0d"],
                ["Обновится", preview.update, "#1677ff"],
                ["С ошибками", preview.errors, preview.errors ? "#cf1322" : undefined],
                ["С предупреждениями", preview.warnings, preview.warnings ? "#d48806" : undefined],
              ] as const
            ).map(([title, value, color]) => (
              <Col xs={12} sm={8} lg={4} key={title}>
                <Statistic title={title} value={value} valueStyle={{ color }} />
              </Col>
            ))}
          </Row>

          {preview.rows.length > 0 && (
            <>
              <Segmented
                style={{ marginBottom: 12 }}
                value={show}
                onChange={(v) => setShow(v as "errors" | "warnings")}
                options={[
                  { value: "errors", label: `Ошибки (${preview.errors})` },
                  { value: "warnings", label: `Предупреждения (${preview.warnings})` },
                ]}
              />
              <Table<RowIssue>
                rowKey="line"
                size="small"
                dataSource={shown}
                pagination={{ pageSize: 20, hideOnSinglePage: true }}
                scroll={{ x: 700 }}
                columns={[
                  { title: "Строка", dataIndex: "line", width: 80 },
                  { title: "Код", dataIndex: "atm_code", width: 140, render: (v) => v || "—" },
                  {
                    title: "Итог",
                    dataIndex: "action",
                    width: 110,
                    render: (a: RowIssue["action"]) => <Tag color={ACTION[a].color}>{ACTION[a].label}</Tag>,
                  },
                  {
                    title: show === "errors" ? "Ошибки" : "Предупреждения (исправлено автоматически)",
                    render: (_, r) => (
                      <Space direction="vertical" size={0}>
                        {(show === "errors" ? r.errors : r.warnings).map((m) => (
                          <Typography.Text key={m} type={show === "errors" ? "danger" : "warning"}>
                            {m}
                          </Typography.Text>
                        ))}
                      </Space>
                    ),
                  },
                ]}
              />
            </>
          )}

          {preview.errors > 0 && (
            <Alert
              type="warning"
              showIcon
              style={{ margin: "12px 0" }}
              message="Строки с ошибками не загрузятся"
              description={
                <Checkbox checked={skipErrors} onChange={(e) => setSkipErrors(e.target.checked)}>
                  Пропустить {preview.errors} строк с ошибками и загрузить остальные
                </Checkbox>
              }
            />
          )}

          <Space style={{ marginTop: 8 }}>
            <Button type="primary" disabled={!canCommit} loading={busy} onClick={commit}>
              Загрузить {preview.create + preview.update} строк
            </Button>
            <Button onClick={check} disabled={busy}>
              Проверить заново
            </Button>
          </Space>
        </>
      )}
    </Card>
  );
}
