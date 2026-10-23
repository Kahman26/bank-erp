import { useQuery } from "@tanstack/react-query";
import { Button, Checkbox, Col, DatePicker, Divider, Drawer, Form, Input, InputNumber, Row, Select } from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useEffect } from "react";

import { api } from "@/api/client";
import { useApiMutation, useReference } from "@/api/hooks";
import type { AtmModel } from "@/api/types";

import type { AtmCard, AtmEdit } from "./types";

type Values = Omit<AtmEdit, "purchase_date" | "commissioning_date"> & {
  purchase_date: Dayjs | null;
  commissioning_date: Dayjs | null;
};

const BOOLS: [keyof AtmEdit, string][] = [
  ["contactless", "Бесконтактный ридер (NFC)"],
  ["screen_sunlight", "Экран для улицы"],
  ["privacy_filter", "Фильтр конфиденциальности"],
  ["audio_jack", "Аудиоразъём для незрячих"],
  ["ups", "ИБП"],
];

/** Создание и редактирование банкомата. Статус и место меняются отдельными операциями. */
export default function AtmForm(props: { open: boolean; onClose: () => void; onSaved: (card: AtmCard) => void; card?: AtmCard }) {
  const { data: ref } = useReference();
  const { data: models = [] } = useQuery({ queryKey: ["atm-models"], queryFn: () => api.get<AtmModel[]>("/atm-models") });
  const [form] = Form.useForm<Values>();
  const editing = props.card;

  useEffect(() => {
    if (!props.open) return;
    form.resetFields();
    if (editing) {
      const e = editing.edit;
      form.setFieldsValue({
        ...e,
        purchase_date: e.purchase_date ? dayjs(e.purchase_date) : null,
        commissioning_date: e.commissioning_date ? dayjs(e.commissioning_date) : null,
      });
    }
  }, [props.open, editing, form]);

  const save = useApiMutation(
    (v: AtmEdit) => (editing ? api.put<AtmCard>(`/atms/${editing.id}`, v) : api.post<AtmCard>("/atms", v)),
    { success: "Сохранено", invalidate: [["atms"], ["atm"]] },
  );

  const submit = async () => {
    const v = await form.validateFields().catch(() => null);
    if (!v) return;
    const card = await save.mutateAsync({
      ...v,
      purchase_date: v.purchase_date?.format("YYYY-MM-DD") ?? null,
      commissioning_date: v.commissioning_date?.format("YYYY-MM-DD") ?? null,
    });
    props.onSaved(card);
    props.onClose();
  };

  const opts = (kind: string) => (ref?.dicts[kind] ?? []).filter((d) => d.is_active).map((d) => ({ value: d.id, label: d.name }));

  return (
    <Drawer
      title={editing ? `Изменение ${editing.atm_code}` : "Новый банкомат"}
      open={props.open}
      onClose={props.onClose}
      width={Math.min(760, window.innerWidth)}
      extra={
        <Button type="primary" onClick={submit} loading={save.isPending}>
          Сохранить
        </Button>
      }
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ currencies: ["UZS"], service_ids: [], scheme_ids: [], contactless: false }}
        onValuesChange={(changed) => {
          // тип устройства по умолчанию берём из модели
          if ("model_id" in changed) {
            const m = models.find((x) => x.id === changed.model_id);
            if (m) form.setFieldValue("device_type_id", m.device_type_id);
          }
        }}
      >
        <Row gutter={12}>
          <Col xs={24} sm={12}>
            <Form.Item name="atm_code" label="Код банкомата" rules={[{ required: true }]} extra="Внутренний код банка, например ATM-TAS-0154">
              <Input />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="serial_number" label="Серийный номер" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="model_id" label="Модель" rules={[{ required: true }]}>
              <Select
                showSearch
                optionFilterProp="label"
                options={models.map((m) => ({ value: m.id, label: `${m.manufacturer_name} ${m.model_name}` }))}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="device_type_id" label="Тип устройства" rules={[{ required: true }]}>
              <Select options={opts("device_type")} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="install_format_id" label="Формат установки" rules={[{ required: true }]}>
              <Select options={opts("install_format")} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="branch_id" label="Ответственный филиал" rules={[{ required: true }]}>
              <Select
                showSearch
                optionFilterProp="label"
                options={ref?.branches.filter((b) => b.is_active).map((b) => ({ value: b.id, label: b.name }))}
              />
            </Form.Item>
          </Col>
          {!editing && (
            <Col xs={24} sm={12}>
              <Form.Item name="status_id" label="Статус" extra="По умолчанию — «На складе банка»">
                <Select allowClear options={opts("atm_status")} />
              </Form.Item>
            </Col>
          )}
          <Col xs={24} sm={12}>
            <Form.Item name="inventory_number" label="Инвентарный номер">
              <Input />
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item name="purchase_date" label="Дата покупки">
              <DatePicker format="DD.MM.YYYY" style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item name="commissioning_date" label="Ввод в эксплуатацию">
              <DatePicker format="DD.MM.YYYY" style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="currencies" label="Валюты" rules={[{ required: true }]}>
              <Select mode="multiple" options={ref?.currencies.map((c) => ({ value: c.code, label: c.code }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="scheme_ids" label="Принимаемые карты">
              <Select mode="multiple" options={ref?.payment_schemes.map((s) => ({ value: s.id, label: s.name }))} />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item name="service_ids" label="Функции">
              <Select mode="multiple" options={opts("atm_service")} />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left" plain>
          Комплектация
        </Divider>
        <Row gutter={12}>
          <Col xs={12} sm={8}>
            <Form.Item name="screen_size_in" label="Диагональ, дюймы">
              <InputNumber min={1} max={60} step={0.1} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={12} sm={8}>
            <Form.Item name="screen_resolution" label="Разрешение">
              <Input placeholder="1280x1024" />
            </Form.Item>
          </Col>
          <Col xs={12} sm={8}>
            <Form.Item name="cassette_count" label="Кассет">
              <InputNumber min={0} max={20} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          {(
            [
              ["screen_orientation_id", "Ориентация экрана", "screen_orientation"],
              ["input_method_id", "Способ ввода", "input_method"],
              ["safe_class_id", "Класс сейфа", "safe_class"],
              ["safe_lock_id", "Замок сейфа", "safe_lock"],
              ["service_access_id", "Доступ для обслуживания", "service_access"],
            ] as const
          ).map(([name, label, kind]) => (
            <Col xs={12} sm={8} key={name}>
              <Form.Item name={name} label={label}>
                <Select allowClear options={opts(kind)} />
              </Form.Item>
            </Col>
          ))}
          {BOOLS.map(([name, label]) => (
            <Col xs={24} sm={12} key={name}>
              <Form.Item name={name} valuePropName="checked" style={{ marginBottom: 8 }}>
                <Checkbox>{label}</Checkbox>
              </Form.Item>
            </Col>
          ))}
          <Col span={24}>
            <Form.Item name="notes" label="Примечание">
              <Input.TextArea rows={2} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Drawer>
  );
}
