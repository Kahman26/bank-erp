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
