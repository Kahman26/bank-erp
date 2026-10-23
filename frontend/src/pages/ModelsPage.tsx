import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  Checkbox,
  Col,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
} from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useReference } from "@/api/hooks";
import type { AtmModel } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";

const MODELS_KEY = ["atm-models"];

type FormValues = Omit<AtmModel, "end_of_support_date"> & { end_of_support_date: Dayjs | null };

const NUMBERS: [keyof AtmModel, string][] = [
  ["height_mm", "Высота, мм"],
  ["width_mm", "Ширина, мм"],
  ["depth_mm", "Глубина, мм"],
  ["weight_kg", "Масса, кг"],
  ["max_cassettes", "Макс. число кассет"],
  ["cassette_capacity", "Ёмкость кассеты, купюр"],
  ["max_notes_per_dispense", "Макс. купюр за выдачу"],
  ["max_denominations", "Макс. число номиналов"],
  ["warranty_months", "Гарантийный срок, мес"],
];

const TEXTS: [keyof AtmModel, string][] = [
  ["screen_options", "Варианты экрана"],
  ["supported_os", "Поддерживаемые ОС"],
  ["power_supply", "Питание"],
  ["operating_temp", "Рабочая температура"],
  ["humidity", "Влажность"],
];

export default function ModelsPage() {
  const { can } = useAuth();
  const { data: ref } = useReference();
  const { data: models = [], isLoading } = useQuery({ queryKey: MODELS_KEY, queryFn: () => api.get<AtmModel[]>("/atm-models") });
  const [editing, setEditing] = useState<AtmModel | "new" | null>(null);
  const [viewing, setViewing] = useState<AtmModel | null>(null);
  const [form] = Form.useForm<FormValues>();
  const canEdit = can("manage_reference");

  const save = useApiMutation(
    (v: Partial<AtmModel>) => (editing === "new" ? api.post("/atm-models", v) : api.put(`/atm-models/${(editing as AtmModel).id}`, v)),
    { success: "Модель сохранена", invalidate: [MODELS_KEY] },
  );
  const remove = useApiMutation((id: number) => api.delete(`/atm-models/${id}`), { success: "Удалено", invalidate: [MODELS_KEY] });

  const formats = Object.fromEntries((ref?.dicts.install_format ?? []).map((d) => [d.id, d.name]));

  const open = (m: AtmModel | "new") => {
    setEditing(m);
    form.resetFields();
    if (m !== "new") form.setFieldsValue({ ...m, end_of_support_date: m.end_of_support_date ? dayjs(m.end_of_support_date) : null });
  };

  const submit = async () => {
    const v = await form.validateFields();
    await save.mutateAsync({ ...v, end_of_support_date: v.end_of_support_date ? v.end_of_support_date.format("YYYY-MM-DD") : null });
    setEditing(null);
  };

  return (
    <Card
      title="Модели банкоматов"
      extra={
        canEdit && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => open("new")}>
            Добавить модель
          </Button>
        )
      }
    >
      <Table<AtmModel>
        rowKey="id"
        loading={isLoading}
        dataSource={models}
        pagination={false}
        scroll={{ x: 900 }}
        onRow={(m) => ({ onClick: () => setViewing(m), style: { cursor: "pointer" } })}
        columns={[
          { title: "Производитель", dataIndex: "manufacturer_name" },
          { title: "Модель", dataIndex: "model_name", render: (v, m) => <b>{m.series ? `${v} (${m.series})` : v}</b> },
          { title: "Тип", dataIndex: "device_type_name" },
          {
            title: "Наличные",
            render: (_, m) => (
              <>
                {m.cash_in && <Tag color="blue">приём</Tag>}
                {m.recycling && <Tag color="purple">рециркуляция</Tag>}
              </>
            ),
          },
          { title: "Кассет, макс.", dataIndex: "max_cassettes" },
          {
            title: "Поддержка до",
            dataIndex: "end_of_support_date",
            render: (d: string | null) =>
              d ? <span style={{ color: dayjs(d).isBefore(dayjs().add(1, "year")) ? "#cf1322" : undefined }}>{dayjs(d).format("DD.MM.YYYY")}</span> : "—",
          },
          { title: "Банкоматов", dataIndex: "atm_count", align: "right" },
        ]}
      />

      <Drawer
        title={viewing ? `${viewing.manufacturer_name} ${viewing.model_name}` : ""}
        open={viewing !== null}
        onClose={() => setViewing(null)}
        width={Math.min(560, window.innerWidth)}
        extra={
          canEdit &&
          viewing && (
            <Space>
              <Button
                onClick={() => {
                  open(viewing);
                  setViewing(null);
                }}
              >
                Изменить
              </Button>
              <Popconfirm
                title="Удалить модель?"
                description="Можно удалить, только если нет банкоматов этой модели"
                onConfirm={() => remove.mutateAsync(viewing.id).then(() => setViewing(null))}
                okText="Удалить"
                cancelText="Отмена"
              >
                <Button danger>Удалить</Button>
              </Popconfirm>
            </Space>
          )
        }
      >
        {viewing && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="Тип устройства">{viewing.device_type_name}</Descriptions.Item>
            <Descriptions.Item label="Форматы установки">{viewing.install_format_ids.map((id) => formats[id]).join(", ") || "—"}</Descriptions.Item>
            <Descriptions.Item label="Приём наличных">{viewing.cash_in ? "да" : "нет"}</Descriptions.Item>
            <Descriptions.Item label="Рециркуляция">{viewing.recycling ? "да" : "нет"}</Descriptions.Item>
            {viewing.height_mm && (
              <Descriptions.Item label="Габариты В×Ш×Г, мм">
                {viewing.height_mm} × {viewing.width_mm} × {viewing.depth_mm}
              </Descriptions.Item>
            )}
            {[...NUMBERS.filter(([k]) => !k.endsWith("_mm")), ...TEXTS].map(([k, label]) =>
              viewing[k] !== null && viewing[k] !== "" ? (
                <Descriptions.Item key={k} label={label}>
                  {String(viewing[k])}
                </Descriptions.Item>
              ) : null,
            )}
            <Descriptions.Item label="Окончание поддержки">
              {viewing.end_of_support_date ? dayjs(viewing.end_of_support_date).format("DD.MM.YYYY") : "—"}
            </Descriptions.Item>
            {viewing.spec_url && (
              <Descriptions.Item label="Спецификация">
                <a href={viewing.spec_url} target="_blank" rel="noreferrer">
                  открыть
                </a>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="Банкоматов в сети">{viewing.atm_count}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      <Drawer
        title={editing === "new" ? "Новая модель" : "Изменение модели"}
        open={editing !== null}
        onClose={() => setEditing(null)}
        width={Math.min(720, window.innerWidth)}
        destroyOnClose
        extra={
          <Button type="primary" onClick={submit} loading={save.isPending}>
            Сохранить
          </Button>
        }
      >
        <Form form={form} layout="vertical" initialValues={{ install_format_ids: [], recycling: false, cash_in: false }}>
          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item name="manufacturer_id" label="Производитель" rules={[{ required: true }]}>
                <Select options={ref?.manufacturers.map((m) => ({ value: m.id, label: m.name }))} showSearch optionFilterProp="label" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="model_name" label="Модель" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="series" label="Серия / семейство">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="device_type_id" label="Тип устройства" rules={[{ required: true }]}>
                <Select options={ref?.dicts.device_type.map((d) => ({ value: d.id, label: d.name }))} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="install_format_ids" label="Допустимые форматы установки">
                <Select mode="multiple" options={ref?.dicts.install_format.map((d) => ({ value: d.id, label: d.name }))} />
              </Form.Item>
            </Col>
            <Col xs={12}>
              <Form.Item name="cash_in" valuePropName="checked">
                <Checkbox>Приём наличных</Checkbox>
              </Form.Item>
            </Col>
            <Col xs={12}>
              <Form.Item name="recycling" valuePropName="checked">
                <Checkbox>Рециркуляция</Checkbox>
              </Form.Item>
            </Col>
            {NUMBERS.map(([k, label]) => (
              <Col xs={12} sm={8} key={k}>
                <Form.Item name={k} label={label}>
                  <InputNumber min={0} style={{ width: "100%" }} />
                </Form.Item>
              </Col>
            ))}
            {TEXTS.map(([k, label]) => (
              <Col xs={24} sm={12} key={k}>
                <Form.Item name={k} label={label}>
                  <Input />
                </Form.Item>
              </Col>
            ))}
            <Col xs={24} sm={12}>
              <Form.Item name="end_of_support_date" label="Окончание поддержки производителем">
                <DatePicker format="DD.MM.YYYY" style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="spec_url" label="Ссылка на спецификацию">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Drawer>
    </Card>
  );
}
