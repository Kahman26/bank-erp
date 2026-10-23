import { useQueryClient } from "@tanstack/react-query";
import { App, Checkbox, Col, DatePicker, Form, Input, InputNumber, Modal, Row, Select, Typography } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import { api } from "@/api/client";
import { useReference } from "@/api/hooks";

import type { AtmCard } from "./types";

/** Договор поставки, стоимость, гарантия и сервисный вендор банкомата. */
export default function ContractModal({ card, open, onClose }: { card: AtmCard; open: boolean; onClose: () => void }) {
  const { data: ref } = useReference();
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [form] = Form.useForm();
  const [busy, setBusy] = useState(false);
  const auto = Form.useWatch("auto_warranty", form);
  const c = card.contract;

  const submit = async () => {
    const v = await form.validateFields().catch(() => null);
    if (!v) return;
    setBusy(true);
    try {
      const updated = await api.put<AtmCard>(`/atms/${card.id}/contract`, {
        ...v,
        warranty_until: v.auto_warranty ? null : (v.warranty_until?.format("YYYY-MM-DD") ?? null),
        price_currency: v.purchase_price != null ? v.price_currency : null,
      });
      qc.setQueryData(["atm", card.id], updated);
      qc.invalidateQueries({ queryKey: ["atms"] });
      message.success("Договор сохранён");
      onClose();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title="Гарантия и договор"
      open={open}
      onCancel={onClose}
      onOk={submit}
      okText="Сохранить"
      confirmLoading={busy}
      destroyOnClose
      afterOpenChange={(o) =>
        o &&
        form.setFieldsValue({
          supplier_id: c?.supplier_id ?? undefined,
          purchase_contract: c?.purchase_contract ?? undefined,
          purchase_price: c?.purchase_price != null ? Number(c.purchase_price) : undefined,
          price_currency: c?.price_currency ?? "USD",
          warranty_until: c?.warranty_until ? dayjs(c.warranty_until) : undefined,
          auto_warranty: false,
          service_vendor_id: c?.service_vendor_id ?? undefined,
          service_sla_hours: c?.service_sla_hours ?? undefined,
        })
      }
    >
      <Form form={form} layout="vertical" preserve={false}>
        <Row gutter={12}>
          <Col xs={24} sm={12}>
            <Form.Item name="warranty_until" label="Окончание гарантийной поддержки">
              <DatePicker format="DD.MM.YYYY" style={{ width: "100%" }} disabled={auto} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="auto_warranty" valuePropName="checked" label=" ">
              <Checkbox>Рассчитать по модели</Checkbox>
            </Form.Item>
          </Col>
        </Row>
        {auto && (
          <Typography.Paragraph type="secondary" style={{ marginTop: -12 }}>
            Дата покупки ({card.main.purchase_date ? dayjs(card.main.purchase_date).format("DD.MM.YYYY") : "не указана"}) +
            гарантийный срок модели.
          </Typography.Paragraph>
        )}
        <Row gutter={12}>
          <Col xs={24} sm={14}>
            <Form.Item name="service_vendor_id" label="Сервисный вендор">
              <Select allowClear options={ref?.vendors.filter((v) => v.is_service).map((v) => ({ value: v.id, label: v.name }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={10}>
            <Form.Item name="service_sla_hours" label="SLA на ремонт, ч">
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={14}>
            <Form.Item name="supplier_id" label="Поставщик">
              <Select allowClear options={ref?.vendors.filter((v) => v.is_supplier).map((v) => ({ value: v.id, label: v.name }))} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={10}>
            <Form.Item name="purchase_contract" label="Договор поставки">
              <Input placeholder="ДП-2024/017 от 12.02.2024" />
            </Form.Item>
          </Col>
          <Col xs={14}>
            <Form.Item name="purchase_price" label="Стоимость покупки">
              <InputNumber min={0} style={{ width: "100%" }} />
            </Form.Item>
          </Col>
          <Col xs={10}>
            <Form.Item name="price_currency" label="Валюта">
              <Select options={ref?.currencies.map((x) => ({ value: x.code, label: x.code }))} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
}
