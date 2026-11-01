<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { clearNextEntry } from '../lib/api';
  import { Power, Gamepad2, RotateCw, X } from '@lucide/svelte';

  const nextEntry = $derived(store.powerStatus?.next_entry);

  function triggerAction(type: 'switch-os' | 'reboot' | 'shutdown', label: string, targetId?: string) {
    store.pendingAction = { type, label, targetId };

    if (store.sessionToken) {
      store.activeModal = 'countdown';
    } else {
      store.activeModal = 'pin';
    }
  }

  async function handleClearNext() {
    try {
      await clearNextEntry(store.sessionToken);
      store.addToast('One-shot boot cleared. System will boot into Linux Server.', 'success');
      if (store.powerStatus) {
        store.powerStatus.next_entry = null;
      }
    } catch (err: any) {
      store.addToast(err.message || 'Failed to clear next entry', 'error');
    }
  }
</script>

<div class="flex flex-col gap-4">
  <!-- Staged One-Shot Boot Alert Banner -->
  {#if nextEntry}
    <aside class="bg-[#182234] border border-sky-400/35 rounded-2xl p-4 shadow-md flex items-center justify-between gap-4 flex-wrap" role="alert">
      <div class="flex items-center gap-3.5">
        <div class="w-9 h-9 rounded-xl bg-sky-500/15 text-sky-400 flex items-center justify-center flex-shrink-0">
          <Gamepad2 class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-sm font-semibold text-white">
            One-Shot Boot Scheduled: <span class="text-sky-300 font-bold">{nextEntry}</span>
          </h2>
          <p class="text-xs text-slate-300">
            The host machine will boot into this OS on next reboot and automatically revert to Linux afterward.
          </p>
        </div>
      </div>
      <button
        type="button"
        onclick={handleClearNext}
        class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-white transition-all cursor-pointer min-h-[36px]"
      >
        <X class="w-4 h-4" />
        <span>Cancel &amp; Keep Linux</span>
      </button>
    </aside>
  {/if}

  <!-- Power Controls Grid -->
  <section aria-labelledby="power-deck-heading" class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h2 id="power-deck-heading" class="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
        <Power class="w-5 h-5 text-sky-400" />
        <span>Power &amp; OS Dual-Boot Deck</span>
      </h2>
      <span class="text-xs text-slate-400 font-medium">PIN Authenticated Host Controls</span>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <!-- Switch to Windows Card -->
      <article class="relative flex flex-col justify-between p-6 bg-[#162036]/90 border border-white/[0.1] hover:border-white/[0.2] rounded-3xl shadow-md hover:-translate-y-0.5 transition-all overflow-hidden group">
        <div class="absolute top-0 left-0 right-0 h-[3px] bg-indigo-500"></div>

        <div>
          <div class="flex items-start justify-between mb-4">
            <div class="w-12 h-12 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 flex items-center justify-center flex-shrink-0">
              <Gamepad2 class="w-6 h-6" />
            </div>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
              One-Shot Boot
            </span>
          </div>

          <h3 class="text-lg font-bold text-white mb-1.5">Switch to Windows 11</h3>
          <p class="text-xs text-slate-300 leading-relaxed mb-5">
            Schedules a one-time reboot into Windows 11 Gaming Mode via GRUB. Automatically reverts to Linux Server on the next boot.
          </p>
        </div>

        <button
          type="button"
          onclick={() => triggerAction('switch-os', 'Switch to Windows 11 Gaming Mode', 'windows')}
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer shadow-sm min-h-[44px]"
        >
          <Gamepad2 class="w-4 h-4" />
          <span>Switch to Windows</span>
        </button>
      </article>

      <!-- Reboot Server Card -->
      <article class="relative flex flex-col justify-between p-6 bg-[#162036]/90 border border-white/[0.1] hover:border-white/[0.2] rounded-3xl shadow-md hover:-translate-y-0.5 transition-all overflow-hidden group">
        <div class="absolute top-0 left-0 right-0 h-[3px] bg-emerald-500"></div>

        <div>
          <div class="flex items-start justify-between mb-4">
            <div class="w-12 h-12 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center justify-center flex-shrink-0">
              <RotateCw class="w-6 h-6" />
            </div>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
              systemd login1
            </span>
          </div>

          <h3 class="text-lg font-bold text-white mb-1.5">Reboot Ubuntu Server</h3>
          <p class="text-xs text-slate-300 leading-relaxed mb-5">
            Performs a clean, orderly restart of the host operating system, flushing storage buffers and restarting homelab containers.
          </p>
        </div>

        <button
          type="button"
          onclick={() => triggerAction('reboot', 'Reboot Ubuntu Server')}
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/35 text-emerald-300 hover:text-emerald-200 transition-all cursor-pointer shadow-sm min-h-[44px]"
        >
          <RotateCw class="w-4 h-4" />
          <span>Reboot Server</span>
        </button>
      </article>

      <!-- Shutdown System Card -->
      <article class="relative flex flex-col justify-between p-6 bg-[#162036]/90 border border-white/[0.1] hover:border-white/[0.2] rounded-3xl shadow-md hover:-translate-y-0.5 transition-all overflow-hidden group">
        <div class="absolute top-0 left-0 right-0 h-[3px] bg-rose-500"></div>

        <div>
          <div class="flex items-start justify-between mb-4">
            <div class="w-12 h-12 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 flex items-center justify-center flex-shrink-0">
              <Power class="w-6 h-6" />
            </div>
            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 border border-rose-500/30 text-rose-300">
              ACPI PowerOff
            </span>
          </div>

          <h3 class="text-lg font-bold text-white mb-1.5">Graceful Shutdown</h3>
          <p class="text-xs text-slate-300 leading-relaxed mb-5">
            Safely powers down host hardware via systemd D-Bus. Use when taking the physical machine offline for maintenance.
          </p>
        </div>

        <button
          type="button"
          onclick={() => triggerAction('shutdown', 'Graceful Host Shutdown')}
          class="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/35 text-rose-300 hover:text-rose-200 transition-all cursor-pointer shadow-sm min-h-[44px]"
        >
          <Power class="w-4 h-4" />
          <span>Power Off System</span>
        </button>
      </article>
    </div>
  </section>
</div>
