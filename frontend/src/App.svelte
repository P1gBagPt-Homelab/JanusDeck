<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { store } from './lib/stores.svelte';
  import { fetchConfig, fetchPowerStatus, fetchServices } from './lib/api';
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
        const flatServices: any[] = [];
        for (const cat of cfg.services) {
          for (const item of cat.items) {
            flatServices.push({ ...item, category: cat.category });
          }
        }
        store.services = flatServices;
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
        store.services = res.services;
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
  <!-- Unlocked Command Deck Dashboard -->
  <div class="flex flex-col min-h-screen bg-ground text-slate-100 animate-in fade-in duration-300">
    <Header />

    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-8">
      <TelemetryDeck />
      <PowerDeck />
      <ServiceDirectory />
    </main>

    <footer class="border-t border-white/[0.08] py-4 bg-[#0b0f19]/80 text-xs text-slate-400">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
        <span>JanusDeck &bull; Project Janus Homelab Command Deck (Svelte 5)</span>
        <span>FastAPI &bull; systemd D-Bus &bull; GNU GRUB &bull; MIT License</span>
      </div>
    </footer>

    <!-- Security & Confirmation Modals (for active power actions while unlocked) -->
    <PinModal />
    <CountdownGate />
  </div>
{/if}

<ToastContainer />
