export type Permission = "view" | "operate" | "edit" | "manage_reference" | "manage_users" | "superadmin";
export type RoleCode = "viewer" | "operator" | "admin" | "superadmin";

export interface Me {
  id: number;
  login: string;
  full_name: string;
  department: string | null;
  role: RoleCode;
  role_label: string;
  permissions: Permission[];
  must_change_password: boolean;
}

export interface UserRow {
  id: number;
  login: string;
  full_name: string;
  department: string | null;
  role: RoleCode;
  is_active: boolean;
  last_login_at: string | null;
  locked_until: string | null;
  created_at: string;
  must_change_password: boolean;
  active_sessions: number;
}

export interface DictItem {
  id: number;
  kind: string;
  code: string;
  name: string;
  sort: number;
  is_active: boolean;
  extra: Record<string, unknown>;
}

export interface Region {
  id: number;
  code: string;
  name: string;
  sort: number;
  center_lat: string | null;
  center_lon: string | null;
}

export interface Branch {
  id: number;
  name: string;
  region_id: number;
  address: string | null;
  is_active: boolean;
}

export interface Manufacturer {
  id: number;
  name: string;
  country: string | null;
  website: string | null;
}

export interface Vendor {
  id: number;
  name: string;
  is_service: boolean;
  is_supplier: boolean;
  contact: string | null;
  ticket_system: string | null;
  is_active: boolean;
}

export interface CodeName {
  id: number;
  code: string;
  name: string;
  sort: number;
}

export interface Currency {
  code: string;
  name: string;
  sort: number;
}

export interface ReferenceBundle {
  dicts: Record<string, DictItem[]>;
  regions: Region[];
  branches: Branch[];
  manufacturers: Manufacturer[];
  vendors: Vendor[];
  processings: CodeName[];
  payment_schemes: CodeName[];
  currencies: Currency[];
  dict_kinds: Record<string, string>;
}

export interface AtmModel {
  id: number;
  manufacturer_id: number;
  manufacturer_name: string;
  model_name: string;
  series: string | null;
  device_type_id: number;
  device_type_name: string;
  install_format_ids: number[];
  height_mm: number | null;
  width_mm: number | null;
  depth_mm: number | null;
  weight_kg: number | null;
  screen_options: string | null;
  max_cassettes: number | null;
  cassette_capacity: number | null;
  max_notes_per_dispense: number | null;
  recycling: boolean;
  cash_in: boolean;
  max_denominations: number | null;
  supported_os: string | null;
  power_supply: string | null;
  operating_temp: string | null;
  humidity: string | null;
  end_of_support_date: string | null;
  warranty_months: number | null;
  spec_url: string | null;
  atm_count: number;
}
