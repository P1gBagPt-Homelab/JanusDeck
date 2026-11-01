import { store } from './stores.svelte';
import { fetchSnapshot } from './api';

let sseSource: EventSource | null = null;
let reconnectAttempts = 0;
let fallbackInterval: ReturnType<typeof setInterval> | null = null;

export function startTelemetryStream() {
  if (sseSource) {
    sseSource.close();
  }

  store.connectionStatus = 'connecting';

  try {
    sseSource = new EventSource('/api/stats');

    sseSource.onopen = () => {
      reconnectAttempts = 0;
      store.connectionStatus = 'online';
      if (fallbackInterval) {
        clearInterval(fallbackInterval);
        fallbackInterval = null;
      }
    };

    sseSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        store.metrics = data;
      } catch (err) {
        console.error('Error parsing SSE telemetry frame:', err);
      }
    };

    sseSource.onerror = () => {
      if (sseSource) {
        sseSource.close();
        sseSource = null;
      }
      reconnectAttempts++;
      store.connectionStatus = 'offline';

      // Fallback: poll snapshot immediately once
      fetchSnapshot().then(data => {
        store.metrics = data;
      }).catch(() => {});

      if (!fallbackInterval) {
        fallbackInterval = setInterval(() => {
          fetchSnapshot().then(data => {
            store.metrics = data;
          }).catch(() => {});
        }, 3000);
      }

      // Exponential backoff reconnect
      const delay = Math.min(10000, 1500 * Math.pow(1.5, reconnectAttempts));
      setTimeout(startTelemetryStream, delay);
    };
  } catch (err) {
    console.warn('SSE not supported or connection error, starting snapshot poll fallback:', err);
    store.connectionStatus = 'offline';
    fetchSnapshot().then(data => store.metrics = data).catch(() => {});
    fallbackInterval = setInterval(() => {
      fetchSnapshot().then(data => store.metrics = data).catch(() => {});
    }, 3000);
  }
}

export function stopTelemetryStream() {
  if (sseSource) {
    sseSource.close();
    sseSource = null;
  }
  if (fallbackInterval) {
    clearInterval(fallbackInterval);
    fallbackInterval = null;
  }
}
