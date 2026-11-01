<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { store } from './lib/stores.svelte';
  import { fetchConfig, fetchPowerStatus, fetchServices, normalizeServices } from './lib/api';
  import { startTelemetryStream, stopTelemetryStream } from './lib/sse';

  import Header from './components/Header.svelte';
  import TelemetryDeck from './components/TelemetryDeck.svelte';
  import PowerDeck from './components/PowerDeck.svelte';
  import ServiceDirectory from './components/ServiceDirectory.svelte';
  import PinModal from './components/PinModal.svelte';
  import CountdownGate from './components/CountdownGate.svelte';
  import ToastContainer from './components/ToastContainer.svelte';

  onMount(async () => {
    // 1. Initial configuration load
    try {
      const cfg = await fetchConfig();
      store.config = cfg;
      if (cfg.server?.title) {
        document.title = `${cfg.server.title} — JanusDeck`;
      }
      if (cfg.services) {
        store.services = normalizeServices(cfg.services);
      }
    } catch (e) {
      console.warn('Could not fetch configuration:', e);
    }
  });

  // Reactive data streaming & health checks active only when unlocked
  $effect(() => {
    if (store.isUnlocked) {
      startTelemetryStream();
      fetchPowerStatus().then(p => {
        store.powerStatus = p;
      }).catch(() => {});
      fetchServices().then(res => {
        store.services = normalizeServices(res.services);
      }).catch(() => {});
    } else {
      stopTelemetryStream();
    }
  });

  onDestroy(() => {
    stopTelemetryStream();
  });
</script>

{#if !store.isUnlocked}
  <!-- Mandatory Security Gate: PIN entry required to access website -->
  <PinModal mandatory={true} />
{:else}
  <main class="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col antialiased selection:bg-sky-500/30 selection:text-sky-200">
    <!-- Header with System Ident & Unlock Toggle -->
    <Header />

    <!-- Main Command Surface -->
    <div class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-8">
      <!-- 1. Live Telemetry Deck -->
      <TelemetryDeck />

      <!-- 2. Dual-Boot & Host Power Controls -->
      <PowerDeck />

      <!-- 3. Homelab Services Directory -->
      <ServiceDirectory />
    </div>

    <!-- Persistent Global Footer -->
    <footer class="mt-auto border-t border-white/[0.06] bg-black/20 py-4 px-6 text-center sm:flex sm:justify-between sm:items-center text-xs text-slate-400">
      <p>JanusDeck • Project Janus Homelab Command Deck (Svelte 5)</p>
      <p class="mt-1 sm:mt-0">FastAPI • systemd D-Bus • GNU GRUB • MIT License</p>
    </footer>

    <!-- Interactive Countdown Safety Gate for destructive actions -->
    <CountdownGate />

    <!-- PIN Unlock / Challenge Modal -->
    <PinModal />

    <!-- Ephemeral Notification Toasts -->
    <ToastContainer />
  </main>
{/if}
