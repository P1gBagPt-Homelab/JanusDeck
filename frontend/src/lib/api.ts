import type { AppPublicConfig, BackupStatusResponse, PowerStatus, ServiceItem } from '../types/config';
import type { TelemetrySnapshot } from '../types/telemetry';

export function normalizeServices(data: any): ServiceItem[] {
  if (!data || !Array.isArray(data)) return [];
  const flat: ServiceItem[] = [];

  for (const entry of data) {
    if (!entry) continue;

    // Category container format: { category: string, items: ServiceItem[] }
    if (Array.isArray(entry.items)) {
      const categoryName = entry.category || 'General';
      for (const item of entry.items) {
        if (item && typeof item === 'object') {
          flat.push({
            ...item,
            category: item.category || categoryName,
          });
        }
      }
    } else if (typeof entry === 'object' && (entry.name || entry.url)) {
      // Individual service item format: { name: string, url: string, ... }
      flat.push(entry);
    }
  }

  return flat;
}

export async function fetchConfig(): Promise<AppPublicConfig> {
  const res = await fetch('/api/config');
  if (!res.ok) throw new Error('Failed to load configuration');
  return res.json();
}

export async function fetchSnapshot(): Promise<TelemetrySnapshot> {
  const res = await fetch('/api/stats/snapshot');
  if (!res.ok) throw new Error('Failed to fetch snapshot');
  return res.json();
}

export async function fetchPowerStatus(): Promise<PowerStatus> {
  const res = await fetch('/api/power/status');
  if (!res.ok) throw new Error('Failed to fetch power status');
  return res.json();
}

export async function fetchServices(): Promise<{ services: ServiceItem[]; checked_at?: string }> {
  const res = await fetch('/api/services');
  if (!res.ok) throw new Error('Failed to fetch services status');
  const data = await res.json();
  return {
    ...data,
    services: normalizeServices(data.services),
  };
}

export async function fetchBackupStatus(): Promise<BackupStatusResponse> {
  const res = await fetch('/api/backup/status');
  if (!res.ok) throw new Error('Failed to fetch backup status');
  return res.json();
}

export async function triggerBackup(
  sessionToken?: string | null,
  pin?: string | null,
  force = false
): Promise<{ success: boolean; message: string; output?: string }> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionToken) {
    headers['X-Session-Token'] = sessionToken;
  }
  if (pin) {
    headers['X-PIN'] = pin;
  }

  const res = await fetch('/api/backup/trigger', {
    method: 'POST',
    headers,
    body: JSON.stringify({ pin: pin || undefined, force }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || data.detail || 'Backup trigger failed');
  }
  return data;
}

export async function verifyPin(pin: string): Promise<{ session_token?: string; expires_in?: number; error?: string }> {
  const res = await fetch('/api/auth/verify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const err: any = new Error(errorData.message || 'Verification failed');
    err.status = res.status;
    err.lockout_remaining_seconds = errorData.lockout_remaining_seconds;
    throw err;
  }
  return res.json();
}

export async function executePowerAction(
  actionType: 'reboot' | 'shutdown' | 'switch-os',
  sessionToken?: string | null,
  pin?: string,
  targetId?: string
): Promise<{ status: string; message: string }> {
  let endpoint = '';
  const body: any = {};

  if (pin) {
    body.pin = pin;
  }

  if (actionType === 'switch-os') {
    endpoint = '/api/power/switch-os';
    body.target_id = targetId || 'windows';
  } else if (actionType === 'reboot') {
    endpoint = '/api/power/reboot';
  } else if (actionType === 'shutdown') {
    endpoint = '/api/power/shutdown';
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionToken) {
    headers['X-Session-Token'] = sessionToken;
  }

  const res = await fetch(endpoint, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || 'Power operation failed');
  }
  return data;
}

export async function clearNextEntry(sessionToken?: string | null): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionToken) {
    headers['X-Session-Token'] = sessionToken;
  }
  const res = await fetch('/api/power/clear-next-entry', {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.message || 'Failed to clear next entry');
  }
}

function getAuthHeaders(pin?: string, sessionToken?: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const effectivePin = pin || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('janus_session_pin') : null);
  const effectiveToken = sessionToken || (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('janus_session_token') : null);
  if (effectivePin) headers['X-Session-Pin'] = effectivePin;
  if (effectiveToken) headers['X-Session-Token'] = effectiveToken;
  return headers;
}

export async function fetchCategories(): Promise<string[]> {
  try {
    const res = await fetch('/api/services/categories');
    if (!res.ok) return [];
    const data = await res.json();
    return data.categories || [];
  } catch {
    return [];
  }
}

export async function createService(
  service: Partial<ServiceItem>,
  pin?: string
): Promise<ServiceItem> {
  const headers = getAuthHeaders(pin);
  const res = await fetch('/api/services', {
    method: 'POST',
    headers,
    body: JSON.stringify(service),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to create service');
  }
  return data.service;
}

export async function updateService(
  id: string,
  service: Partial<ServiceItem>,
  pin?: string
): Promise<ServiceItem> {
  const headers = getAuthHeaders(pin);
  const res = await fetch(`/api/services/${id}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(service),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to update service');
  }
  return data.service;
}

export async function deleteService(
  id: string,
  pin?: string
): Promise<{ status: string; id: string }> {
  const headers = getAuthHeaders(pin);
  const res = await fetch(`/api/services/${id}`, {
    method: 'DELETE',
    headers,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to delete service');
  }
  return data;
}

export async function reorderServices(
  orders: { id: string; display_order: number }[],
  pin?: string
): Promise<void> {
  const headers = getAuthHeaders(pin);
  const res = await fetch('/api/services/reorder', {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ orders }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to reorder services');
  }
}
