import type { AppPublicConfig, PowerStatus, ServiceItem } from '../types/config';
import type { TelemetrySnapshot } from '../types/telemetry';

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

export async function fetchServices(): Promise<{ services: ServiceItem[] }> {
  const res = await fetch('/api/services');
  if (!res.ok) throw new Error('Failed to fetch services status');
  return res.json();
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
