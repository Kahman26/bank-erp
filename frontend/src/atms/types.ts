export interface AtmRow {
  id: number;
  atm_code: string;
  status_code: string;
  status: string;
  manufacturer: string;
  model: string;
  device_type: string;
  branch: string;
  region: string;
  city_district: string | null;
  address: string | null;
  place_type: string | null;
  latitude: string | null;
  longitude: string | null;
  is_24h: boolean | null;
  contactless: boolean;
  commissioning_date: string | null;
  warranty_until: string | null;
  terminal_id: string | null;
  currencies: string | null;
}

export interface AtmPage {
  items: AtmRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface MapPoints {
  points: [number, string, number, number, string][];
  total: number;
  without_location: number;
}

export interface AtmEdit {
  atm_code: string;
  serial_number: string;
  inventory_number: string | null;
  model_id: number;
  device_type_id: number;
  install_format_id: number;
  branch_id: number;
  purchase_date: string | null;
  commissioning_date: string | null;
  notes: string | null;
  screen_size_in: string | null;
  screen_resolution: string | null;
  screen_orientation_id: number | null;
  input_method_id: number | null;
  screen_sunlight: boolean | null;
  privacy_filter: boolean | null;
  safe_class_id: number | null;
  safe_lock_id: number | null;
  service_access_id: number | null;
  cassette_count: number | null;
  contactless: boolean;
  audio_jack: boolean | null;
  ups: boolean | null;
  currencies: string[];
  service_ids: number[];
  scheme_ids: number[];
  status_id?: number | null;
}

export interface LocationInfo {
  id: number;
  name: string;
  region: string;
  city_district: string;
  address: string;
  landmark: string | null;
  latitude: number;
  longitude: number;
  place_type: string;
  indoor: boolean;
  is_24h: boolean;
  working_hours: string;
  premises_owner: string | null;
  site_contact: string | null;
}

export interface Processing {
  id: number;
  processing_id: number;
  processing: string;
  terminal_id: string;
  merchant_id: string;
  host_protocol_id: number | null;
  host_protocol: string | null;
  connection_type_id: number | null;
  connection_type: string | null;
  ip_address: string | null;
}

export interface Certificate {
  id: number;
  object: "model" | "atm" | "module";
  object_label: string;
  cert_type: string;
  payment_scheme: string | null;
  cert_number: string;
  issued_at: string;
  valid_until: string;
  status: "valid" | "expiring" | "expired" | "renewal" | "revoked";
  status_label: string;
  needs_review: boolean;
  source: string | null;
}

export interface AtmCard {
  id: number;
  atm_code: string;
  edit: AtmEdit;
  updated_at: string;
  header: {
    status_code: string;
    status: string;
    model: string;
    model_id: number;
    device_type: string;
    address: string | null;
    allowed_status_ids: number[];
    has_place: boolean;
    current_place_from: string | null;
  };
  main: {
    serial_number: string;
    inventory_number: string | null;
    install_format: string;
    branch: string;
    purchase_date: string | null;
    commissioning_date: string | null;
    decommission_date: string | null;
    currencies: string[];
    services: string[];
    schemes: string[];
    notes: string | null;
    model_cash_in: boolean;
    model_recycling: boolean;
    end_of_support_date: string | null;
  };
  config: Record<string, string | number | boolean | null>;
  location: LocationInfo | null;
  placements: {
    id: number;
    placed_from: string;
    placed_to: string | null;
    move_reason: string | null;
    basis_document: string | null;
    location: LocationInfo;
  }[];
  processings: Processing[];
  modules: {
    id: number;
    module_type_id: number;
    type: string;
    xfs: string | null;
    vendor: string | null;
    model: string | null;
    serial_number: string;
    firmware_version: string | null;
    installed_at: string;
    removed_at: string | null;
    is_faulty: boolean;
    attributes: Record<string, string | number>;
  }[];
  software: { id: number; type: string; name: string; version: string; installed_at: string | null }[];
  service_events: {
    id: number;
    type: string;
    ticket_number: string | null;
    started_at: string;
    finished_at: string | null;
    downtime_hours: number | null;
    problem: string;
    work_done: string | null;
    affects_certification: boolean;
    performer: string;
    cost: string | null;
    cost_currency: string | null;
    replacements: { removed: string; installed: string }[];
  }[];
  certificates: Certificate[];
  status_history: { status: string; changed_at: string; changed_by: string | null; comment: string | null }[];
  contract: {
    supplier: string | null;
    purchase_contract: string | null;
    purchase_price: string | null;
    price_currency: string | null;
    warranty_until: string | null;
    service_vendor: string | null;
    service_sla_hours: number | null;
  } | null;
}
