import { PlusOutlined } from "@ant-design/icons";
import { Button, Card, Checkbox, Form, Input, InputNumber, Menu, Modal, Popconfirm, Select, Space, Table, Tabs, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { REFERENCE_KEY, useApiMutation, useReference } from "@/api/hooks";
import type { DictItem, ReferenceBundle } from "@/api/types";

/** Простые списки: слева виды, справа значения выбранного вида. */
function DictsTab({ data: ref }: { data: ReferenceBundle }) {
  const kinds = Object.entries(ref.dict_kinds);
  const [kind, setKind] = useState(kinds[0][0]);
  const [editing, setEditing] = useState<DictItem | "new" | null>(null);
  const [form] = Form.useForm();

  const save = useApiMutation(
    (v: Partial<DictItem>) =>
      editing === "new" ? api.post(`/reference/dicts/${kind}`, v) : api.patch(`/reference/dicts/items/${(editing as DictItem).id}`, v),
    { success: "Сохранено", invalidate: [REFERENCE_KEY] },
  );

  const submit = async () => {
    const v = await form.validateFields().catch(() => null);
    if (!v) return;
    await save.mutateAsync(editing === "new" ? v : { name: v.name, sort: v.sort, is_active: v.is_active });
    setEditing(null);
  };

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      <Menu
        style={{ width: 260, flex: "0 0 auto" }}
        selectedKeys={[kind]}
        items={kinds.map(([k, label]) => ({ key: k, label }))}
        onClick={({ key }) => setKind(key)}
      />
      <div style={{ flex: "1 1 400px", minWidth: 0 }}>
        <Space style={{ marginBottom: 12 }}>
          <Button
            icon={<PlusOutlined />}
            onClick={() => {
              setEditing("new");
              form.setFieldsValue({ sort: (ref.dicts[kind]?.length ?? 0) * 10, is_active: true });
            }}
          >
            Добавить значение
          </Button>
        </Space>
        <Table<DictItem>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={ref.dicts[kind] ?? []}
          columns={[
            { title: "Название", dataIndex: "name" },
            { title: "Код", dataIndex: "code", render: (c: string) => <code>{c}</code> },
            { title: "Порядок", dataIndex: "sort", width: 90 },
            {
              title: "Статус",
              dataIndex: "is_active",
              width: 110,
              render: (a: boolean) => (a ? <Tag color="green">Активно</Tag> : <Tag>Скрыто</Tag>),
            },
            {
              width: 100,
              render: (_, item) => (
                <Button
                  size="small"
                  onClick={() => {
                    setEditing(item);
                    form.setFieldsValue(item);
                  }}
                >
                  Изменить
                </Button>
              ),
            },
          ]}
        />
      </div>
      <Modal title={ref.dict_kinds[kind]} open={editing !== null} onOk={submit} onCancel={() => setEditing(null)} okText="Сохранить" destroyOnClose>
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="code"
            label="Код"
            extra="Латиница в нижнем регистре, цифры и _ — используется при загрузке файлов"
            rules={[{ required: true, pattern: /^[a-z0-9_]+$/ }]}
          >
            <Input disabled={editing !== "new"} />
          </Form.Item>
          <Form.Item name="sort" label="Порядок">
            <InputNumber />
          </Form.Item>
          <Form.Item name="is_active" valuePropName="checked">
            <Checkbox>Показывать в списках</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

interface Field {
  name: string;
  label: string;
  input?: ReactNode;
  checkbox?: boolean;
  required?: boolean;
}

/** Таблица-справочник с формой: регионы, филиалы, производители и т. п. */
function TableTab<T extends { id: number }>(props: {
  path: string;
  rows: T[];
  columns: ColumnsType<T>;
  fields: Field[];
  defaults?: Partial<T>;
}) {
  const [editing, setEditing] = useState<T | "new" | null>(null);
  const [form] = Form.useForm();
  const save = useApiMutation(
    (v: Partial<T>) => (editing === "new" ? api.post(`/reference/${props.path}`, v) : api.put(`/reference/${props.path}/${(editing as T).id}`, v)),
    { success: "Сохранено", invalidate: [REFERENCE_KEY] },
  );
  const remove = useApiMutation((id: number) => api.delete(`/reference/${props.path}/${id}`), {
    success: "Удалено",
    invalidate: [REFERENCE_KEY],
  });

  const submit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return;
    await save.mutateAsync(values);
    setEditing(null);
  };

  return (
    <>
      <Button
        icon={<PlusOutlined />}
        style={{ marginBottom: 12 }}
        onClick={() => {
          setEditing("new");
          form.setFieldsValue(props.defaults ?? {});
        }}
      >
        Добавить
      </Button>
      <Table<T>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={props.rows}
        scroll={{ x: 600 }}
        columns={[
          ...props.columns,
          {
            width: 190,
            render: (_, row) => (
              <Space>
                <Button
                  size="small"
                  onClick={() => {
                    setEditing(row);
                    form.setFieldsValue(row);
                  }}
                >
                  Изменить
                </Button>
                <Popconfirm title="Удалить запись?" onConfirm={() => remove.mutate(row.id)} okText="Удалить" cancelText="Отмена">
                  <Button size="small" danger>
                    Удалить
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal open={editing !== null} title={editing === "new" ? "Новая запись" : "Изменение"} onOk={submit} onCancel={() => setEditing(null)} okText="Сохранить" destroyOnClose>
        <Form form={form} layout="vertical" preserve={false}>
          {props.fields.map((f) =>
            f.checkbox ? (
              <Form.Item key={f.name} name={f.name} valuePropName="checked">
                <Checkbox>{f.label}</Checkbox>
              </Form.Item>
            ) : (
              <Form.Item key={f.name} name={f.name} label={f.label} rules={f.required ? [{ required: true }] : []}>
                {f.input ?? <Input />}
              </Form.Item>
            ),
          )}
        </Form>
      </Modal>
    </>
  );
}

export default function ReferencePage() {
  const { data: ref } = useReference();
  if (!ref) return <Card loading />;
  const regionName = Object.fromEntries(ref.regions.map((r) => [r.id, r.name]));
  const regionSelect = <Select options={ref.regions.map((r) => ({ value: r.id, label: r.name }))} showSearch optionFilterProp="label" />;
  const codeName: Field[] = [
    { name: "name", label: "Название", required: true },
    { name: "code", label: "Код", required: true },
    { name: "sort", label: "Порядок", input: <InputNumber /> },
  ];

  return (
    <Card title="Справочники">
      <Tabs
        items={[
          { key: "dicts", label: "Списки значений", children: <DictsTab data={ref} /> },
          {
            key: "branches",
            label: "Филиалы",
            children: (
              <TableTab
                path="branches"
                rows={ref.branches}
                defaults={{ is_active: true }}
                columns={[
                  { title: "Название", dataIndex: "name" },
                  { title: "Регион", dataIndex: "region_id", render: (id: number) => regionName[id] },
                  { title: "Адрес", dataIndex: "address" },
                ]}
                fields={[
                  { name: "name", label: "Название", required: true },
                  { name: "region_id", label: "Регион", required: true, input: regionSelect },
                  { name: "address", label: "Адрес" },
                  { name: "is_active", label: "Действует", checkbox: true },
                ]}
              />
            ),
          },
          {
            key: "vendors",
            label: "Вендоры и поставщики",
            children: (
              <TableTab
                path="vendors"
                rows={ref.vendors}
                defaults={{ is_service: true, is_active: true }}
                columns={[
                  { title: "Название", dataIndex: "name" },
                  {
                    title: "Роль",
                    render: (_, v) => (
                      <>
                        {v.is_service && <Tag color="blue">Сервис</Tag>}
                        {v.is_supplier && <Tag color="purple">Поставщик</Tag>}
                      </>
                    ),
                  },
                  { title: "Система заявок", dataIndex: "ticket_system" },
                  { title: "Контакт", dataIndex: "contact" },
                ]}
                fields={[
                  { name: "name", label: "Название", required: true },
                  { name: "is_service", label: "Ремонтирует банкоматы", checkbox: true },
                  { name: "is_supplier", label: "Поставляет оборудование", checkbox: true },
                  { name: "ticket_system", label: "Система заявок" },
                  { name: "contact", label: "Контакт" },
                  { name: "is_active", label: "Действует", checkbox: true },
                ]}
              />
            ),
          },
          {
            key: "manufacturers",
            label: "Производители",
            children: (
              <TableTab
                path="manufacturers"
                rows={ref.manufacturers}
                columns={[
                  { title: "Название", dataIndex: "name" },
                  { title: "Страна", dataIndex: "country" },
                  { title: "Сайт", dataIndex: "website" },
                ]}
                fields={[
                  { name: "name", label: "Название", required: true },
                  { name: "country", label: "Страна" },
                  { name: "website", label: "Сайт" },
                ]}
              />
            ),
          },
          {
            key: "regions",
            label: "Регионы",
            children: (
              <TableTab
                path="regions"
                rows={ref.regions}
                columns={[
                  { title: "Название", dataIndex: "name" },
                  { title: "Код", dataIndex: "code" },
                  { title: "Центр", render: (_, r) => (r.center_lat ? `${r.center_lat}, ${r.center_lon}` : "—") },
                ]}
                fields={[
                  ...codeName,
                  { name: "center_lat", label: "Широта центра", input: <InputNumber style={{ width: "100%" }} step={0.000001} /> },
                  { name: "center_lon", label: "Долгота центра", input: <InputNumber style={{ width: "100%" }} step={0.000001} /> },
                ]}
              />
            ),
          },
          {
            key: "processings",
            label: "Процессинги",
            children: (
              <TableTab path="processings" rows={ref.processings} columns={[{ title: "Название", dataIndex: "name" }, { title: "Код", dataIndex: "code" }]} fields={codeName} />
            ),
          },
          {
            key: "schemes",
            label: "Платёжные системы",
            children: (
              <TableTab
                path="payment-schemes"
                rows={ref.payment_schemes}
                columns={[{ title: "Название", dataIndex: "name" }, { title: "Код", dataIndex: "code" }]}
                fields={codeName}
              />
            ),
          },
        ]}
      />
    </Card>
  );
}
