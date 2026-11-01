<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { Zap, Server, Clock, Lock, Unlock } from '@lucide/svelte';

  function formatUptime(seconds?: number): string {
    if (!seconds || seconds <= 0) return 'Just started';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);

    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0 || days > 0) parts.push(`${hours}h`);
    parts.push(`${mins}m`);
    return parts.join(' ');
  }

  function toggleLock() {
    if (store.sessionToken) {
      store.setSession(null);
      store.addToast('Website locked. Master PIN required to view.', 'info');
    } else {
      store.pendingAction = {
        type: 'unlock_only',
        label: 'Unlock Website'
      };
      store.activeModal = 'pin';
    }
  }

  const hostname = $derived(store.metrics?.host?.hostname || 'Janus Server');
  const osName = $derived(store.metrics?.host?.os || 'Linux');
  const uptime = $derived(formatUptime(store.metrics?.host?.uptime_seconds));
  const isUnlocked = $derived(store.isUnlocked);
</script>

<header class="sticky top-0 z-30 bg-[#0b0f19]/90 backdrop-blur-md border-b border-white/[0.08] py-3.5 px-4 sm:px-6 lg:px-8">
  <div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
    <!-- Brand -->
    <div class="flex items-center gap-3.5">
      <div class="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-400/30 flex items-center justify-center text-sky-400 shadow-sm flex-shrink-0">
        <Zap class="w-5 h-5" />
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white leading-tight">
          {store.config?.server?.title || 'Janus Lab'}
        </h1>
        <p class="text-xs text-slate-400 font-normal">
          {store.config?.server?.subtitle || 'Hybrid Gaming & On-Demand Server'}
        </p>
      </div>
    </div>

    <!-- Status Badges & Controls -->
    <div class="flex items-center gap-2.5 sm:gap-3 flex-wrap">
      <!-- Live SSE Connection Pill -->
      <div
        class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors
        {store.connectionStatus === 'online' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : ''}
        {store.connectionStatus === 'connecting' ? 'bg-amber-500/10 border-amber-500/30 text-amber-300' : ''}
        {store.connectionStatus === 'offline' ? 'bg-rose-500/10 border-rose-500/30 text-rose-300' : ''}"
        role="status"
      >
        <span class="relative flex h-2 w-2">
          {#if store.connectionStatus === 'online'}
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          {/if}
          <span class="relative inline-flex rounded-full h-2 w-2 {store.connectionStatus === 'online' ? 'bg-emerald-400' : store.connectionStatus === 'connecting' ? 'bg-amber-400' : 'bg-rose-400'}"></span>
        </span>
        <span class="capitalize">{store.connectionStatus}</span>
      </div>

      <!-- Host Platform Pill (Desktop) -->
      <div class="hidden md:inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs bg-white/[0.04] border border-white/[0.08] text-slate-300">
        <Server class="w-3.5 h-3.5 text-sky-400" />
        <span>{hostname} ({osName})</span>
      </div>

      <!-- Host Uptime Pill -->
      <div class="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs bg-white/[0.04] border border-white/[0.08] text-slate-300 tabular-nums">
        <Clock class="w-3.5 h-3.5 text-indigo-400" />
        <span>{uptime}</span>
      </div>

      <!-- Lock / Unlock Session Button -->
      <button
        type="button"
        onclick={toggleLock}
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer min-h-[32px]
        {isUnlocked ? 'bg-sky-500/15 border-sky-400/40 text-sky-300' : 'bg-white/[0.04] border-white/[0.08] text-slate-300 hover:bg-white/[0.08] hover:text-white'}"
        aria-label="Toggle PIN security lock state"
      >
        {#if isUnlocked}
          <Unlock class="w-3.5 h-3.5 text-sky-400" />
          <span>Unlocked</span>
        {:else}
          <Lock class="w-3.5 h-3.5" />
          <span>PIN Guarded</span>
        {/if}
      </button>
    </div>
  </div>
</header>
