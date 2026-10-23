import { FilterOutlined } from "@ant-design/icons";
import { Badge, Button, Col, Collapse, Row, Select, Space } from "antd";
import { useSearchParams } from "react-router-dom";

import { useReference } from "@/api/hooks";

/** Фильтры живут в адресной строке: список и карта открываются с одними и теми же параметрами. */
export const FILTER_KEYS = [
  "region_id",
  "branch_id",
  "status_id",
  "manufacturer_id",
  "model_id",
  "device_type_id",
  "install_format_id",
  "place_type_id",
  "processing_id",
  "vendor_id",
  "currency",
  "contactless",
  "cash_in",
  "is_24h",
  "has_location",
  "warranty_expiring_days",
  "cert_expiring_days",
  "repair_over_days",
] as const;

const NON_FILTER = new Set(["page", "page_size", "sort", "order"]);

export function filterParams(params: URLSearchParams): URLSearchParams {
  const result = new URLSearchParams();
  params.forEach((value, key) => {
    if (!NON_FILTER.has(key)) result.append(key, value);
  });
  return result;
}

export function activeFilterCount(params: URLSearchParams): number {
  return new Set([...filterParams(params).keys()].filter((k) => k !== "q")).size;
}

type Option = { value: string; label: string };

export default function FilterPanel({ models }: { models?: { id: number; manufacturer_name: string; model_name: string }[] }) {
  const { data: ref } = useReference();
  const [params, setParams] = useSearchParams();

  const set = (key: string, values: string[] | string | undefined) => {
    const next = new URLSearchParams(params);
    next.delete(key);
    next.delete("page");
    for (const v of Array.isArray(values) ? values : values ? [values] : []) next.append(key, v);
    setParams(next, { replace: true });
  };

  const multi = (key: string, placeholder: string, options: Option[]) => (
    <Select
      mode="multiple"
      allowClear
      maxTagCount="responsive"
      placeholder={placeholder}
      style={{ width: "100%" }}
      value={params.getAll(key)}
      onChange={(v: string[]) => set(key, v)}
      options={options}
      optionFilterProp="label"
    />
  );

  const single = (key: string, placeholder: string, options: Option[]) => (
    <Select
      allowClear
      placeholder={placeholder}
      style={{ width: "100%" }}
      value={params.get(key) ?? undefined}
      onChange={(v?: string) => set(key, v)}
      options={options}
    />
  );

  const dict = (kind: string): Option[] => (ref?.dicts[kind] ?? []).map((d) => ({ value: String(d.id), label: d.name }));
  const yesNo = (yes: string, no: string): Option[] => [
    { value: "true", label: yes },
    { value: "false", label: no },
  ];
  const days = (label: string): Option[] =>
    [30, 90, 180, 365].map((d) => ({ value: String(d), label: `${label} ${d} дн.` }));

  const regionIds = params.getAll("region_id").map(Number);
  const branches = (ref?.branches ?? [])
    .filter((b) => !regionIds.length || regionIds.includes(b.region_id))
    .map((b) => ({ value: String(b.id), label: b.name }));

  const count = activeFilterCount(params);
  const col = { xs: 24, sm: 12, lg: 8, xl: 6 };

  return (
    <Collapse
      size="small"
      style={{ marginBottom: 12 }}
      items={[
        {
          key: "f",
          label: (
            <Space>
              <FilterOutlined />
              Фильтры
              {count > 0 && <Badge count={count} color="#1F4E79" />}
            </Space>
          ),
          extra:
            count > 0 ? (
              <Button
                size="small"
                type="link"
                onClick={(e) => {
                  e.stopPropagation();
                  const next = new URLSearchParams();
                  ["q", "sort", "order", "page_size"].forEach((k) => params.get(k) && next.set(k, params.get(k)!));
                  setParams(next, { replace: true });
                }}
              >
                Сбросить
              </Button>
            ) : null,
          children: (
            <Row gutter={[12, 12]}>
              <Col {...col}>{multi("region_id", "Регион", (ref?.regions ?? []).map((r) => ({ value: String(r.id), label: r.name })))}</Col>
              <Col {...col}>{multi("branch_id", "Филиал", branches)}</Col>
              <Col {...col}>{multi("status_id", "Статус", dict("atm_status"))}</Col>
              <Col {...col}>
                {multi("manufacturer_id", "Производитель", (ref?.manufacturers ?? []).map((m) => ({ value: String(m.id), label: m.name })))}
              </Col>
              <Col {...col}>
                {multi(
                  "model_id",
                  "Модель",
                  (models ?? []).map((m) => ({ value: String(m.id), label: `${m.manufacturer_name} ${m.model_name}` })),
                )}
              </Col>
              <Col {...col}>{multi("device_type_id", "Тип устройства", dict("device_type"))}</Col>
              <Col {...col}>{multi("install_format_id", "Формат установки", dict("install_format"))}</Col>
              <Col {...col}>{multi("place_type_id", "Тип места", dict("place_type"))}</Col>
              <Col {...col}>
                {multi("processing_id", "Процессинг", (ref?.processings ?? []).map((p) => ({ value: String(p.id), label: p.name })))}
              </Col>
              <Col {...col}>
                {multi(
                  "vendor_id",
                  "Сервисный вендор",
                  (ref?.vendors ?? []).filter((v) => v.is_service).map((v) => ({ value: String(v.id), label: v.name })),
                )}
              </Col>
              <Col {...col}>{multi("currency", "Валюта", (ref?.currencies ?? []).map((c) => ({ value: c.code, label: `${c.code} — ${c.name}` })))}</Col>
              <Col {...col}>{single("contactless", "Бесконтактный ридер", yesNo("Есть NFC", "Без NFC"))}</Col>
              <Col {...col}>{single("cash_in", "Приём наличных", yesNo("С приёмом", "Только выдача"))}</Col>
              <Col {...col}>{single("is_24h", "Режим работы", yesNo("Круглосуточно", "По графику"))}</Col>
              <Col {...col}>{single("has_location", "Место установки", yesNo("Установлен", "Не установлен"))}</Col>
              <Col {...col}>{single("cert_expiring_days", "Сертификат истекает", days("в течение"))}</Col>
              <Col {...col}>{single("warranty_expiring_days", "Гарантия истекает", days("в течение"))}</Col>
              <Col {...col}>
                {single(
                  "repair_over_days",
                  "В ремонте дольше",
                  [1, 3, 7, 14].map((d) => ({ value: String(d), label: `${d} дн.` })),
                )}
              </Col>
            </Row>
          ),
        },
      ]}
    />
  );
}
