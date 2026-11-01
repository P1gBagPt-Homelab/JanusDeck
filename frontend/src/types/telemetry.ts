export interface HostMetadata {
  hostname: string;
  os: string;
  release?: string;
  architecture?: string;
  uptime_seconds?: number;
  boot_timestamp?: string;
}

export interface CpuFrequency {
  current_mhz: number;
  min_mhz?: number | null;
  max_mhz?: number | null;
}

export interface CpuTelemetry {
  enabled: boolean;
  label?: string;
  usage_percent: number;
  per_core_percent?: number[];
  core_count_logical?: number;
  core_count_physical?: number;
  frequency?: CpuFrequency;
  temperature_c?: number | null;
}

export interface SwapTelemetry {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  usage_percent: number;
}

export interface MemoryTelemetry {
  enabled: boolean;
  label?: string;
  total_bytes: number;
  used_bytes: number;
  available_bytes: number;
  total_gb: number;
  used_gb: number;
  available_gb: number;
  usage_percent: number;
  swap?: SwapTelemetry;
}

export interface GpuVramTelemetry {
  total_bytes?: number;
  used_bytes?: number;
  free_bytes?: number;
  total_gb?: number;
  used_gb?: number;
  free_gb?: number;
  usage_percent?: number;
}

export interface GpuTelemetry {
  enabled: boolean;
  available: boolean;
  label?: string;
  device_name?: string;
  device_index?: number;
  usage_percent?: number;
  memory_usage_percent?: number;
  vram?: GpuVramTelemetry;
  temperature_c?: number | null;
  power_watts?: number | null;
  status?: string;
  error?: string;
}

export interface StoragePoolTelemetry {
  name: string;
  path: string;
  available: boolean;
  total_bytes?: number;
  used_bytes?: number;
  free_bytes?: number;
  total_gb?: number;
  used_gb?: number;
  free_gb?: number;
  usage_percent?: number;
  error?: string;
}

export interface StorageTelemetry {
  pools: StoragePoolTelemetry[];
}

export interface TelemetrySnapshot {
  timestamp: string;
  host?: HostMetadata;
  cpu?: CpuTelemetry;
  memory?: MemoryTelemetry;
  gpu?: GpuTelemetry;
  storage?: StorageTelemetry;
}
