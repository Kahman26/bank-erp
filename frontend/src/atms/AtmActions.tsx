import { DownOutlined } from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  App,
  Button,
  Checkbox,
  Col,
  DatePicker,
  Divider,
  Dropdown,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Row,
  Select,
  Typography,
} from "antd";
import dayjs, { type Dayjs } from "dayjs";
import { useState } from "react";

import { api } from "@/api/client";
import { useReference } from "@/api/hooks";

import LocationPicker from "./LocationPicker";
import type { AtmCard } from "./types";

type Action = "status" | "move" | "repair" | "module" | "software";

const DATE = "DD.MM.YYYY";
const DATETIME = "DD.MM.YYYY HH:mm";
const iso = (d: Dayjs | null | undefined) => (d ? d.format("YYYY-MM-DD") : undefined);

/** Общая отправка: ответ — обновлённая карточка, сразу кладём её в кэш. */
function useSubmit(card: AtmCard, onDone: () => void) {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const [busy, setBusy] = useState(false);
  const run = async (path: string, body: unknown, success: string) => {
    setBusy(true);
    try {
      const updated = await api.post<AtmCard>(`/atms/${card.id}${path}`, body);
      qc.setQueryData(["atm", card.id], updated);
      qc.invalidateQueries({ queryKey: ["atms"] });
      qc.invalidateQueries({ queryKey: ["atm-map"] });
      message.success(success);
      onDone();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return { run, busy };
}

function StatusModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm();
  const { run, busy } = useSubmit(card, onClose);
  const statusId = Form.useWatch("status_id", form);
  const statuses = (ref?.dicts.atm_status ?? []).filter((s) => card.header.allowed_status_ids.includes(s.id));
  const target = statuses.find((s) => s.id === statusId);
  const needsPlace = target && ["installing", "in_service", "repair", "vendor_repair"].includes(target.code) && !card.header.has_place;

  return (
    <Modal
      title="Смена статуса"
      open={open}
      onCancel={onClose}
      okText="Сменить"
      confirmLoading={busy}
      okButtonProps={{ disabled: !!needsPlace }}
      destroyOnClose
      onOk={async () => {
        const v = await form.validateFields().catch(() => null);
        if (!v) return;
        await run("/status", { ...v, effective_date: iso(v.effective_date) }, "Статус изменён");
      }}
    >
      <Typography.Paragraph>
        Сейчас: <b>{card.header.status}</b>
      </Typography.Paragraph>
      {statuses.length === 0 ? (
        <Alert type="info" message="Из этого статуса переходов нет" />
      ) : (
        <Form form={form} layout="vertical" preserve={false} initialValues={{ effective_date: dayjs() }}>
          <Form.Item name="status_id" label="Новый статус" rules={[{ required: true }]}>
            <Select options={statuses.map((s) => ({ value: s.id, label: s.name }))} />
          </Form.Item>
          {needsPlace && (
            <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="Сначала укажите место установки (действие «Установить на место»)" />
          )}
          {target && ["in_stock", "on_farm", "written_off", "in_delivery"].includes(target.code) && card.header.has_place && (
            <Alert type="info" showIcon style={{ marginBottom: 12 }} message="Банкомат будет снят с текущего места — размещение закроется этой датой" />
          )}
          <Form.Item name="effective_date" label="Дата">
            <DatePicker format={DATE} disabledDate={(d) => d.isAfter(dayjs(), "day")} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="comment" label="Комментарий">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      )}
    </Modal>
  );
}

function MoveModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm();
  const { run, busy } = useSubmit(card, onClose);
  const lat = Form.useWatch(["location", "latitude"], form);
  const lon = Form.useWatch(["location", "longitude"], form);
  const regionId = Form.useWatch(["location", "region_id"], form);
  const region = ref?.regions.find((r) => r.id === regionId);
  const center: [number, number] = region?.center_lat ? [Number(region.center_lat), Number(region.center_lon)] : [41.311, 69.24];
  const installing = ref?.dicts.atm_status.find((s) => s.code === "installing");
  const canStartInstall = !card.header.has_place && installing && card.header.allowed_status_ids.includes(installing.id);
  const opts = (kind: string) => (ref?.dicts[kind] ?? []).filter((d) => d.is_active).map((d) => ({ value: d.id, label: d.name }));

  return (
    <Modal
      title={card.header.has_place ? "Перемещение банкомата" : "Установка на место"}
      open={open}
      onCancel={onClose}
      okText={card.header.has_place ? "Переместить" : "Установить"}
      confirmLoading={busy}
      width={Math.min(820, window.innerWidth)}
      destroyOnClose
      onOk={async () => {
        const v = await form.validateFields().catch(() => null);
        if (!v) return;
        await run(
          "/move",
          {
            ...v,
            placed_from: iso(v.placed_from),
            set_status_id: v.start_install && installing ? installing.id : undefined,
            start_install: undefined,
          },
          card.header.has_place ? "Банкомат перемещён" : "Банкомат установлен",
        );
      }}
    >
      {card.header.has_place && (
        <Typography.Paragraph type="secondary">
          Текущее размещение ({card.header.address}) закроется датой перемещения, история сохранится.
        </Typography.Paragraph>
      )}
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        initialValues={{
          placed_from: dayjs(),
          start_install: !!canStartInstall,
          // регион по умолчанию — регион ответственного филиала
          location: {
            indoor: true,
            is_24h: false,
            region_id: ref?.branches.find((b) => b.id === card.edit.branch_id)?.region_id ?? ref?.regions[0]?.id,
          },
        }}
      >
        <Row gutter={12}>
          <Col span={24}>
            <Form.Item label="Точка на карте (кликните, чтобы поставить метку)" style={{ marginBottom: 8 }}>
              <LocationPicker
                lat={lat}
                lon={lon}
                center={center}
                onPick={(la, lo) =>
                  form.setFieldsValue({ location: { latitude: Number(la.toFixed(6)), longitude: Number(lo.toFixed(6)) } })
                }
              />
            </Form.Item>
          </Col>
          <Col xs={12} sm={6}>
            <Form.Item name={["location", "latitude"]} label="Широта" rules={[{ required: true, type: "number", min: 37, max: 46 }]}>
              <InputNumber step={0.000001} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={12} sm={6}>
            <Form.Item name={["location", "longitude"]} label="Долгота" rules={[{ required: true, type: "number", min: 55, max: 74 }]}>
              <InputNumber step={0.000001} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "region_id"]} label="Регион" rules={[{ required: true }]}>
              <Select options={ref?.regions.map((r) => ({ value: r.id, label: r.name }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "city_district"]} label="Город / район" rules={[{ required: true }]}>
              <Input placeholder="Юнусабадский район" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "address"]} label="Адрес" rules={[{ required: true }]}>
              <Input placeholder="ул. Амира Темура, 1" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "name"]} label="Название точки" rules={[{ required: true }]}>
              <Input placeholder="ТЦ «Бахор», 1 этаж" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "landmark"]} label="Ориентир">
              <Input placeholder="напротив станции метро" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name={["location", "place_type_id"]} label="Тип места" rules={[{ required: true }]}>
              <Select options={opts("place_type")} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name={["location", "access_type_id"]} label="Доступ">
              <Select allowClear options={opts("access_type")} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name={["location", "working_hours"]} label="Режим работы" rules={[{ required: true }]}>
              <Input placeholder="Круглосуточно" />
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item name={["location", "indoor"]} valuePropName="checked" style={{ marginBottom: 8 }}>
              <Checkbox>В помещении</Checkbox>
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item name={["location", "is_24h"]} valuePropName="checked" style={{ marginBottom: 8 }}>
              <Checkbox>Круглосуточно</Checkbox>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "site_contact"]} label="Контакт на объекте">
              <Input />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name={["location", "premises_owner"]} label="Владелец помещения">
              <Input />
            </Form.Item>
          </Col>
        </Row>
        <Divider style={{ margin: "8px 0 16px" }} />
        <Row gutter={12}>
          <Col xs={24} sm={8}>
            <Form.Item name="placed_from" label={card.header.has_place ? "Дата перемещения" : "Дата установки"} rules={[{ required: true }]}>
              <DatePicker format={DATE} disabledDate={(d) => d.isAfter(dayjs(), "day")} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name="move_reason_id" label="Причина">
              <Select allowClear options={opts("move_reason")} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={8}>
            <Form.Item name="basis_document" label="Основание">
              <Input placeholder="Приказ №…" />
            </Form.Item>
          </Col>
          {canStartInstall && (
            <Col span={24}>
              <Form.Item name="start_install" valuePropName="checked">
                <Checkbox>Перевести банкомат в статус «В установке»</Checkbox>
              </Form.Item>
            </Col>
          )}
        </Row>
      </Form>
    </Modal>
  );
}

function RepairModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm();
  const { run, busy } = useSubmit(card, onClose);
  const performer = Form.useWatch("performer", form);
  const finished = Form.useWatch("finished", form);
  const installed = card.modules.filter((m) => !m.removed_at);
  const moduleOptions = installed.map((m) => ({ value: m.id, label: `${m.type} · ${m.serial_number}` }));

  return (
    <Modal
      title="Регистрация ремонта"
      open={open}
      onCancel={onClose}
      okText="Зарегистрировать"
      confirmLoading={busy}
      width={Math.min(760, window.innerWidth)}
      destroyOnClose
      onOk={async () => {
        const v = await form.validateFields().catch(() => null);
        if (!v) return;
        await run(
          "/service-events",
          {
            event_type_id: v.event_type_id,
            started_at: v.started_at.toISOString(),
            finished_at: v.finished ? v.finished_at?.toISOString() : null,
            ticket_number: v.ticket_number,
            problem: v.problem,
            work_done: v.work_done,
            module_id: v.module_id,
            vendor_id: v.performer === "vendor" ? v.vendor_id : null,
            by_bank_engineer: v.performer === "bank",
            cost: v.cost,
            cost_currency: v.cost ? v.cost_currency : null,
            replacements: v.replacements ?? [],
            set_repair_status: !v.finished && v.set_repair_status,
          },
          "Ремонт зарегистрирован",
        );
      }}
    >
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        initialValues={{ started_at: dayjs(), performer: "vendor", finished: false, set_repair_status: true, cost_currency: "USD" }}
      >
        <Row gutter={12}>
          <Col xs={24} sm={12}>
            <Form.Item name="event_type_id" label="Тип события" rules={[{ required: true }]}>
              <Select options={ref?.dicts.service_event_type.map((d) => ({ value: d.id, label: d.name }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="started_at" label="Начало (обнаружение)" rules={[{ required: true }]}>
              <DatePicker showTime format={DATETIME} disabledDate={(d) => d.isAfter(dayjs(), "day")} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item name="problem" label="Описание неисправности" rules={[{ required: true }]}>
              <Input.TextArea rows={2} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="performer" label="Исполнитель">
              <Radio.Group
                options={[
                  { value: "vendor", label: "Сервисный вендор" },
                  { value: "bank", label: "Инженер банка" },
                ]}
              />
            </Form.Item>
          </Col>
          {performer === "vendor" && (
            <>
              <Col xs={24} sm={12}>
                <Form.Item name="vendor_id" label="Вендор" rules={[{ required: true }]}>
                  <Select options={ref?.vendors.filter((v) => v.is_service && v.is_active).map((v) => ({ value: v.id, label: v.name }))} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="ticket_number" label="Номер заявки в системе вендора">
                  <Input />
                </Form.Item>
              </Col>
            </>
          )}
          <Col xs={24} sm={12}>
            <Form.Item name="module_id" label="Неисправный узел">
              <Select allowClear options={moduleOptions} />
            </Form.Item>
          </Col>
        </Row>

        <Divider orientation="left" plain style={{ margin: "4px 0 12px" }}>
          Замена узлов
        </Divider>
        <Form.List name="replacements">
          {(fields, { add, remove }) => (
            <>
              {fields.map((f) => (
                <Row gutter={8} key={f.key} align="bottom">
                  <Col xs={24} sm={9}>
                    <Form.Item name={[f.name, "removed_module_id"]} label="Снимаемый узел" rules={[{ required: true }]}>
                      <Select options={moduleOptions} />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={5}>
                    <Form.Item name={[f.name, "serial_number"]} label="Серийный № нового" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={5}>
                    <Form.Item name={[f.name, "model"]} label="Модель нового">
                      <Input placeholder="как у старого" />
                    </Form.Item>
                  </Col>
                  <Col xs={18} sm={4}>
                    <Form.Item name={[f.name, "firmware_version"]} label="Прошивка">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={6} sm={1}>
                    <Form.Item>
                      <Button type="text" danger onClick={() => remove(f.name)}>
                        ✕
                      </Button>
                    </Form.Item>
                  </Col>
                </Row>
              ))}
              <Button onClick={() => add()} style={{ marginBottom: 12 }}>
                Добавить замену узла
              </Button>
              {fields.length > 0 && (
                <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
                  Замена картридера, NFC-ридера или PIN-клавиатуры отмечается как влияющая на сертификацию, а сертификаты
                  снятого узла — как требующие проверки.
                </Typography.Paragraph>
              )}
            </>
          )}
        </Form.List>

        <Form.Item name="finished" valuePropName="checked" style={{ marginBottom: 8 }}>
          <Checkbox>Ремонт уже завершён</Checkbox>
        </Form.Item>
        {finished ? (
          <Row gutter={12}>
            <Col xs={24} sm={12}>
              <Form.Item name="finished_at" label="Окончание" rules={[{ required: true }]}>
                <DatePicker showTime format={DATETIME} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={12} sm={6}>
              <Form.Item name="cost" label="Стоимость">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={12} sm={6}>
              <Form.Item name="cost_currency" label="Валюта">
                <Select options={ref?.currencies.map((c) => ({ value: c.code, label: c.code }))} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="work_done" label="Выполненные работы">
                <Input.TextArea rows={2} />
              </Form.Item>
            </Col>
          </Row>
        ) : (
          <Form.Item name="set_repair_status" valuePropName="checked">
            <Checkbox>Перевести банкомат в статус «На ремонте» / «На ремонте у вендора»</Checkbox>
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}

export function CloseRepairModal({ card, eventId, onClose }: { card: AtmCard; eventId: number | null; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm();
  const { run, busy } = useSubmit(card, onClose);
  const event = card.service_events.find((e) => e.id === eventId);
  return (
    <Modal
      title="Закрытие ремонта"
      open={eventId !== null}
      onCancel={onClose}
      okText="Закрыть ремонт"
      confirmLoading={busy}
      destroyOnClose
      onOk={async () => {
        const v = await form.validateFields().catch(() => null);
        if (!v) return;
        await run(
          `/service-events/${eventId}/close`,
          { ...v, finished_at: v.finished_at.toISOString(), cost_currency: v.cost ? v.cost_currency : null },
          "Ремонт закрыт",
        );
      }}
    >
      {event && (
        <Typography.Paragraph type="secondary">
          {event.problem} · с {dayjs(event.started_at).format(DATETIME)} · {event.performer}
        </Typography.Paragraph>
      )}
      <Form
        form={form}
        layout="vertical"
        preserve={false}
        initialValues={{ finished_at: dayjs(), return_to_service: true, cost_currency: "USD" }}
      >
        <Form.Item name="finished_at" label="Окончание" rules={[{ required: true }]}>
          <DatePicker showTime format={DATETIME} disabledDate={(d) => d.isAfter(dayjs(), "day")} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="work_done" label="Выполненные работы">
          <Input.TextArea rows={2} />
        </Form.Item>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="cost" label="Стоимость">
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="cost_currency" label="Валюта">
              <Select options={ref?.currencies.map((c) => ({ value: c.code, label: c.code }))} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="return_to_service" valuePropName="checked">
          <Checkbox>Вернуть банкомат в эксплуатацию</Checkbox>
        </Form.Item>
      </Form>
    </Modal>
  );
}

function ModuleModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm();
  const { run, busy } = useSubmit(card, onClose);
  return (
    <Modal
      title="Новый узел"
      open={open}
      onCancel={onClose}
      okText="Добавить"
      confirmLoading={busy}
      destroyOnClose
      onOk={async () => {
        const v = await form.validateFields().catch(() => null);
        if (!v) return;
        await run("/modules", { ...v, installed_at: iso(v.installed_at) }, "Узел добавлен");
      }}
    >
      <Form form={form} layout="vertical" preserve={false} initialValues={{ installed_at: dayjs() }}>
        <Form.Item name="module_type_id" label="Тип узла" rules={[{ required: true }]}>
          <Select
            options={ref?.dicts.module_type.map((d) => ({ value: d.id, label: d.extra.xfs ? `${d.name} (${d.extra.xfs})` : d.name }))}
          />
        </Form.Item>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="vendor" label="Производитель">
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="model" label="Модель">
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="serial_number" label="Серийный номер" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="firmware_version" label="Прошивка">
              <Input />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="installed_at" label="Дата установки">
          <DatePicker format={DATE} style={{ width: "100%" }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function SoftwareModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const [form] = Form.useForm();
  const { run, busy } = useSubmit(card, onClose);
  return (
    <Modal
      title="Установка или обновление ПО"
      open={open}
      onCancel={onClose}
      okText="Сохранить"
      confirmLoading={busy}
      destroyOnClose
      onOk={async () => {
        const v = await form.validateFields().catch(() => null);
        if (!v) return;
        await run("/software", { ...v, installed_at: iso(v.installed_at) }, "ПО записано");
      }}
    >
      <Typography.Paragraph type="secondary">Каждое обновление — новая запись: история версий сохраняется.</Typography.Paragraph>
      <Form form={form} layout="vertical" preserve={false} initialValues={{ installed_at: dayjs() }}>
        <Form.Item name="software_type_id" label="Тип ПО" rules={[{ required: true }]}>
          <Select options={ref?.dicts.software_type.map((d) => ({ value: d.id, label: d.name }))} />
        </Form.Item>
        <Row gutter={12}>
          <Col span={14}>
            <Form.Item name="name" label="Название" rules={[{ required: true }]}>
              <Input placeholder="KAL Kalignite" />
            </Form.Item>
          </Col>
          <Col span={10}>
            <Form.Item name="version" label="Версия" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="installed_at" label="Дата установки">
          <DatePicker format={DATE} style={{ width: "100%" }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

/** Кнопка «Действия» в карточке банкомата и все окна операций. */
export default function AtmActions({ card }: { card: AtmCard }) {
  const [open, setOpen] = useState<Action | null>(null);
  const close = () => setOpen(null);
  const writtenOff = card.header.status_code === "written_off";
  return (
    <>
      <Dropdown
        trigger={["click"]}
        menu={{
          onClick: ({ key }) => setOpen(key as Action),
          items: [
            { key: "status", label: "Сменить статус", disabled: card.header.allowed_status_ids.length === 0 },
            { key: "move", label: card.header.has_place ? "Переместить" : "Установить на место", disabled: writtenOff },
            { key: "repair", label: "Зарегистрировать ремонт", disabled: writtenOff },
            { type: "divider" },
            { key: "module", label: "Добавить узел", disabled: writtenOff },
            { key: "software", label: "Установить / обновить ПО", disabled: writtenOff },
          ],
        }}
      >
        <Button type="primary">
          Действия <DownOutlined />
        </Button>
      </Dropdown>
      <StatusModal card={card} open={open === "status"} onClose={close} />
      <MoveModal card={card} open={open === "move"} onClose={close} />
      <RepairModal card={card} open={open === "repair"} onClose={close} />
      <ModuleModal card={card} open={open === "module"} onClose={close} />
      <SoftwareModal card={card} open={open === "software"} onClose={close} />
    </>
  );
}
