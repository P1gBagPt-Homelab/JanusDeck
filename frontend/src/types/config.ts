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
  backup?: {
    enabled: boolean;
    backup_dir: string;
    rclone_remote: string;
    retention_days_local: number;
    retention_days_cloud: number;
  };
}

export interface BackupSnapshot {
  filename: string;
  size_bytes: number;
  size_formatted: string;
  created_at: string;
  date: string;
  is_today: boolean;
  age_days: number;
  relative_time: string;
}

export interface BackupStatusResponse {
  backup_dir: string;
  directory_exists: boolean;
  today_done: boolean;
  today_date: string;
  today_backup: BackupSnapshot | null;
  latest_backup: BackupSnapshot | null;
  total_backups: number;
  total_size_bytes: number;
  total_size_formatted: string;
  backups: BackupSnapshot[];
  rclone_remote: string;
  retention_days_local?: number;
  retention_days_cloud?: number;
  message?: string;
}

export interface PowerStatus {
  dbus_available: boolean;
  grub_available: boolean;
  next_entry: string | null;
  default_entry?: string | null;
  simulation_mode: boolean;
  os_targets: OsTarget[];
}
