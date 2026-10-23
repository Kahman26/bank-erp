export type CertStatus = "valid" | "expiring" | "expired" | "renewal" | "revoked";

export const CERT_STATUS: Record<CertStatus, { label: string; color: string }> = {
  valid: { label: "Действует", color: "green" },
  expiring: { label: "Истекает", color: "orange" },
  expired: { label: "Истёк", color: "red" },
  renewal: { label: "На продлении", color: "blue" },
  revoked: { label: "Отозван", color: "default" },
};

export interface CertRow {
  id: number;
  object: "model" | "atm" | "module";
  atm_model_id: number | null;
  atm_id: number | null;
  atm_code: string | null;
  model: string | null;
  module_id: number | null;
  module_type: string | null;
  module_serial: string | null;
  module_removed_at: string | null;
  cert_type_id: number;
  cert_type: string;
  payment_scheme_id: number | null;
  payment_scheme: string | null;
  cert_number: string;
  issued_at: string;
  valid_until: string;
  manual_status: string | null;
  status: CertStatus;
  needs_review: boolean;
  source_id: number | null;
  source: string | null;
  has_document: boolean;
  atm_count: number;
}

export interface CertPage {
  items: CertRow[];
  total: number;
}

export interface CertSummary {
  valid: number;
  expiring: number;
  expired: number;
  renewal: number;
  revoked: number;
  needs_review: number;
  modules_without: number;
}

export interface WithoutCertRow {
  id: number;
  serial_number: string;
  installed_at: string;
  module_type: string;
  atm_id: number;
  atm_code: string;
  model: string;
}
