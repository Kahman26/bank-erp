import { useQuery } from "@tanstack/react-query";
import { App, Col, DatePicker, Form, Input, Modal, Radio, Row, Select } from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { useReference } from "@/api/hooks";
import type { AtmModel } from "@/api/types";
import type { AtmCard, AtmPage } from "@/atms/types";

import type { CertRow } from "./types";

type ObjectKind = "model" | "atm" | "module";

/**
 * Создание и изменение сертификата. Из карточки банкомата объект ограничен этим банкоматом
 * и его узлами (atm), из реестра — любая модель, банкомат или узел.
 */
export default function CertForm(props: {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  cert?: CertRow;
  atm?: AtmCard;
}) {
  const { data: ref } = useReference();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [busy, setBusy] = useState(false);
  const [atmSearch, setAtmSearch] = useState("");
  const kind: ObjectKind = Form.useWatch("object", form) ?? "atm";
  const atmId: number | undefined = Form.useWatch("atm_id", form) ?? props.atm?.id;
  const certTypeId = Form.useWatch("cert_type_id", form);
  const isScheme = ref?.dicts.cert_type.find((t) => t.id === certTypeId)?.code === "scheme";

  const { data: models = [] } = useQuery({ queryKey: ["atm-models"], queryFn: () => api.get<AtmModel[]>("/atm-models") });
  const { data: found } = useQuery({
    queryKey: ["atm-search", atmSearch],
    queryFn: () => api.get<AtmPage>(`/atms?q=${encodeURIComponent(atmSearch)}&page_size=20`),
    enabled: !props.atm && props.open,
  });
  const { data: atmCard } = useQuery({
    queryKey: ["atm", atmId],
    queryFn: () => api.get<AtmCard>(`/atms/${atmId}`),
    enabled: !!atmId && kind === "module" && !props.atm,
  });
  const modules = (props.atm ?? atmCard)?.modules.filter((m) => !m.removed_at) ?? [];

  useEffect(() => {
    if (!props.open) return;
    form.resetFields();
    const c = props.cert;
    if (c) {
      form.setFieldsValue({
        ...c,
        object: c.object,
        atm_id: c.object === "module" ? c.atm_id : (c.atm_id ?? undefined),
        issued_at: dayjs(c.issued_at),
        valid_until: dayjs(c.valid_until),
      });
      if (c.atm_code) setAtmSearch(c.atm_code);
    } else {
      form.setFieldsValue({ object: props.atm ? "module" : "model", atm_id: props.atm?.id, issued_at: dayjs() });
    }
  }, [props.open, props.cert, props.atm, form]);

  const submit = async () => {
    const v = await form.validateFields().catch(() => null);
    if (!v) return;
    const body = {
      atm_model_id: v.object === "model" ? v.atm_model_id : null,
      atm_id: v.object === "atm" ? (props.atm?.id ?? v.atm_id) : null,
      module_id: v.object === "module" ? v.module_id : null,
      cert_type_id: v.cert_type_id,
      payment_scheme_id: v.payment_scheme_id ?? null,
      cert_number: v.cert_number,
      issued_at: v.issued_at.format("YYYY-MM-DD"),
      valid_until: v.valid_until.format("YYYY-MM-DD"),
      source_id: v.source_id ?? null,
    };
    setBusy(true);
    try {
      if (props.cert) await api.put(`/certificates/${props.cert.id}`, body);
      else await api.post("/certificates", body);
      message.success("Сертификат сохранён");
      props.onSaved();
      props.onClose();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const atmOptions = (found?.items ?? []).map((a) => ({ value: a.id, label: `${a.atm_code} · ${a.manufacturer} ${a.model}` }));

  return (
    <Modal
      title={props.cert ? "Изменение сертификата" : "Новый сертификат"}
      open={props.open}
      onCancel={props.onClose}
      onOk={submit}
      okText="Сохранить"
      confirmLoading={busy}
      width={Math.min(640, window.innerWidth)}
      destroyOnClose
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item name="object" label="На что выдан">
          <Radio.Group
            options={[
              ...(props.atm ? [] : [{ value: "model", label: "Модель" }]),
              { value: "atm", label: "Банкомат" },
              { value: "module", label: "Узел банкомата" },
            ]}
          />
        </Form.Item>
        {kind === "model" && (
          <Form.Item name="atm_model_id" label="Модель" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={models.map((m) => ({ value: m.id, label: `${m.manufacturer_name} ${m.model_name}` }))} />
          </Form.Item>
        )}
        {kind !== "model" && !props.atm && (
          <Form.Item name="atm_id" label="Банкомат" rules={[{ required: true }]}>
            <Select
              showSearch
              filterOption={false}
              onSearch={setAtmSearch}
              placeholder="Код или Terminal ID"
              options={atmOptions}
              onChange={() => form.setFieldValue("module_id", undefined)}
            />
          </Form.Item>
        )}
        {kind === "module" && (
          <Form.Item name="module_id" label="Узел" rules={[{ required: true }]} extra="Обычно картридер, NFC-ридер или PIN-клавиатура">
            <Select options={modules.map((m) => ({ value: m.id, label: `${m.type} · ${m.serial_number}` }))} />
          </Form.Item>
        )}
        <Row gutter={12}>
          <Col xs={24} sm={14}>
            <Form.Item name="cert_type_id" label="Вид сертификата" rules={[{ required: true }]}>
              <Select options={ref?.dicts.cert_type.map((t) => ({ value: t.id, label: t.name }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={10}>
            <Form.Item name="payment_scheme_id" label="Платёжная система" rules={[{ required: isScheme }]}>
              <Select allowClear options={ref?.payment_schemes.map((s) => ({ value: s.id, label: s.name }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="cert_number" label="Номер (Letter of Approval)" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="source_id" label="Кем предоставлен">
              <Select allowClear options={ref?.dicts.cert_source.map((t) => ({ value: t.id, label: t.name }))} />
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item name="issued_at" label="Дата выдачи" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={12}>
            <Form.Item
              name="valid_until"
              label="Действует до"
              dependencies={["issued_at"]}
              rules={[
                { required: true },
                ({ getFieldValue }) => ({
                  validator: (_, v) =>
                    !v || !getFieldValue("issued_at") || !v.isBefore(getFieldValue("issued_at"))
                      ? Promise.resolve()
                      : Promise.reject(new Error("Раньше даты выдачи")),
                }),
              ]}
            >
              <DatePicker format="DD.MM.YYYY" style={{ width: "100%" }} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
}
