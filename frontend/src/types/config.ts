export interface ServerConfig {
  title: string;
  subtitle: string;
  refresh_interval_ms: number;
}

export interface SecurityConfig {
  pin_required: boolean;
  session_timeout_seconds: number;
}

export interface OsTarget {
  id: string;
  name: string;
  icon?: string;
  grub_entry: string;
  description?: string;
}

export interface PowerConfig {
  allow_shutdown: boolean;
  allow_reboot: boolean;
  allow_os_switch: boolean;
  os_targets: OsTarget[];
}

export interface ServiceItem {
  name: string;
  url: string;
  external_url?: string;
  icon?: string;
  description?: string;
  health_check_url?: string;
  online?: boolean;
  status?: 'online' | 'offline' | 'degraded';
  response_time_ms?: number;
  latency_ms?: number;
  status_code?: number;
  error?: string;
  category?: string;
  last_checked?: string;
}

export interface ServiceCategory {
  category: string;
  items: ServiceItem[];
}

export interface AppPublicConfig {
  server: ServerConfig;
  security: SecurityConfig;
  power: PowerConfig;
  telemetry: any;
  services: ServiceCategory[];
}

export interface PowerStatus {
  dbus_available: boolean;
  grub_available: boolean;
  next_entry: string | null;
  default_entry?: string | null;
  simulation_mode: boolean;
  os_targets: OsTarget[];
}
