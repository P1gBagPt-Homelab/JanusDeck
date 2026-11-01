import type { TelemetrySnapshot } from '../types/telemetry';
import type { PowerStatus, ServiceItem, AppPublicConfig } from '../types/config';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'info' | 'success' | 'error';
  duration?: number;
}

// Svelte 5 Runes-based Reactive Store
class DashboardStore {
  // Config
  config = $state<AppPublicConfig | null>(null);

  // Connection & Telemetry
  connectionStatus = $state<'online' | 'connecting' | 'offline'>('connecting');
  metrics = $state<TelemetrySnapshot | null>(null);

  // Power & Boot
  powerStatus = $state<PowerStatus | null>(null);

  // Services
  services = $state<ServiceItem[]>([]);
  isCheckingServices = $state(false);

  // Auth & Session
  sessionToken = $state<string | null>(
    typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('janus_session_token') : null
  );

  // Modal & Pending Action
  activeModal = $state<'none' | 'pin' | 'countdown'>('none');
  pendingAction = $state<{
    type: 'reboot' | 'shutdown' | 'switch-os' | 'unlock_only';
    targetId?: string;
    label: string;
  } | null>(null);

  // Toasts
  toasts = $state<ToastMessage[]>([]);

  setSession(token: string | null) {
    this.sessionToken = token;
    if (typeof sessionStorage !== 'undefined') {
      if (token) {
        sessionStorage.setItem('janus_session_token', token);
      } else {
        sessionStorage.removeItem('janus_session_token');
      }
    }
  }

  addToast(message: string, type: 'info' | 'success' | 'error' = 'info', duration = 3500) {
    const id = Math.random().toString(36).substring(2, 9);
    this.toasts.push({ id, message, type, duration });
    setTimeout(() => {
      this.removeToast(id);
    }, duration);
  }

  removeToast(id: string) {
    this.toasts = this.toasts.filter(t => t.id !== id);
  }
}

export const store = new DashboardStore();
