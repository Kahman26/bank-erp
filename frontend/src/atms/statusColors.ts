import { brand } from "@/theme/brand";

/** Shared by maps, charts and labelled status tags. */
export const STATUS_COLORS: Record<string, string> = {
  in_service: brand.green,
  repair: "#A86B16",
  vendor_repair: brand.error,
  installing: brand.greenMuted,
  in_delivery: "#437F8E",
  in_stock: "#596B7C",
  on_farm: "#77618F",
  to_writeoff: "#8B6B38",
  written_off: "#808080",
};
