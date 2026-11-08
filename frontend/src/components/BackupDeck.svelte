<script lang="ts">
  import { onMount } from 'svelte';
  import { store } from '../lib/stores.svelte';
  import { fetchBackupStatus, triggerBackup } from '../lib/api';
  import {
    Archive,
    CheckCircle2,
    AlertCircle,
    RotateCw,
    Play,
    HardDrive,
    Cloud,
    Calendar,
    FileArchive,
  } from '@lucide/svelte';

  let isTriggering = $state(false);
  let searchQuery = $state('');

  const status = $derived(store.backupStatus);

  const filteredBackups = $derived.by(() => {
    if (!status?.backups) return [];
    if (!searchQuery.trim()) return status.backups;
    const q = searchQuery.toLowerCase();
    return status.backups.filter(
      (b) =>
        b.filename.toLowerCase().includes(q) ||
        b.date.toLowerCase().includes(q) ||
        b.relative_time.toLowerCase().includes(q)
    );
  });

  async function refreshBackups() {
    store.isCheckingBackups = true;
    try {
      const res = await fetchBackupStatus();
      store.backupStatus = res;
    } catch (err: any) {
      console.warn('Could not refresh backup status:', err);
    } finally {
      store.isCheckingBackups = false;
    }
  }

  async function handleTriggerBackup(force = false) {
    if (isTriggering) return;
    isTriggering = true;
    try {
      const res = await triggerBackup(store.sessionToken, store.cachedPin, force);
      store.addToast(res.message || 'Automated backup completed successfully.', 'success');
      await refreshBackups();
    } catch (err: any) {
      store.addToast(err.message || 'Failed to trigger backup.', 'error');
    } finally {
      isTriggering = false;
    }
  }

  onMount(() => {
    if (!store.backupStatus) {
      refreshBackups();
    }
  });
</script>

<section aria-labelledby="backup-deck-heading" class="flex flex-col gap-4">
  <!-- Section Title & Global Actions -->
  <div class="flex items-center justify-between flex-wrap gap-2">
    <div>
      <h2 id="backup-deck-heading" class="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
        <Archive class="w-5 h-5 text-sky-400" />
        <span>Automated Backups</span>
      </h2>
      <p class="text-xs text-slate-400">
        Local snapshots &amp; zero-knowledge AES-256 encrypted sync to 5TB Google Drive
      </p>
    </div>

    <div class="flex items-center gap-2">
      <button
        type="button"
        onclick={refreshBackups}
        disabled={store.isCheckingBackups}
        aria-label="Refresh backup inventory"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-white transition-all cursor-pointer disabled:opacity-50"
      >
        <RotateCw class="w-3.5 h-3.5 {store.isCheckingBackups ? 'animate-spin text-sky-400' : ''}" />
        <span>Refresh</span>
      </button>

      <button
        type="button"
        onclick={() => handleTriggerBackup(false)}
        disabled={isTriggering}
        class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-sky-500/20 hover:bg-sky-500/30 border border-sky-400/30 text-sky-200 transition-all cursor-pointer shadow-sm disabled:opacity-50"
      >
        <Play class="w-3.5 h-3.5 {isTriggering ? 'animate-pulse text-sky-300' : ''}" />
        <span>{isTriggering ? 'Running...' : 'Run Backup Now'}</span>
      </button>
    </div>
  </div>

  {#if status}
    <!-- Hero Status Banner: Today's Backup Done or Not Done -->
    {#if status.today_done}
      <aside
        class="relative overflow-hidden bg-gradient-to-r from-emerald-950/60 via-[#102422]/90 to-[#102422]/70 border border-emerald-500/30 rounded-2xl p-5 shadow-lg flex items-center justify-between gap-4 flex-wrap"
        role="status"
      >
        <div class="flex items-start gap-3.5">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center flex-shrink-0 mt-0.5">
            <CheckCircle2 class="w-6 h-6" />
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h3 class="text-base font-bold text-white">Today's Backup Completed</h3>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Up to Date
              </span>
            </div>
            {#if status.today_backup}
              <p class="text-xs text-slate-300 mt-1">
                Archive: <span class="font-mono text-emerald-300">{status.today_backup.filename}</span>
                <span class="text-slate-400 mx-1.5">•</span>
                Size: <span class="font-semibold text-white">{status.today_backup.size_formatted}</span>
                <span class="text-slate-400 mx-1.5">•</span>
                Date: <span class="text-slate-300">{status.today_date}</span>
              </p>
            {/if}
            <p class="text-[11px] text-slate-400 mt-0.5">
              Local snapshot archived &amp; zero-knowledge sync verified with <span class="text-sky-300 font-mono">{status.rclone_remote}</span>.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            onclick={() => handleTriggerBackup(true)}
            disabled={isTriggering}
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-slate-200 transition-all cursor-pointer disabled:opacity-50"
          >
            <Play class="w-3.5 h-3.5 text-slate-300" />
            <span>Force New Backup</span>
          </button>
        </div>
      </aside>
    {:else}
      <aside
        class="relative overflow-hidden bg-gradient-to-r from-amber-950/60 via-[#2a2215]/90 to-[#2a2215]/70 border border-amber-500/35 rounded-2xl p-5 shadow-lg flex items-center justify-between gap-4 flex-wrap"
        role="alert"
      >
        <div class="flex items-start gap-3.5">
          <div class="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 text-amber-400 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertCircle class="w-6 h-6" />
          </div>
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <h3 class="text-base font-bold text-white">Today's Backup Pending</h3>
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Not Done Today ({status.today_date})
              </span>
            </div>
            <p class="text-xs text-slate-300 mt-1">
              No backup snapshot has been created yet today. The automated pipeline runs on host boot and hourly via cron.
            </p>
            {#if status.latest_backup}
              <p class="text-[11px] text-slate-400 mt-0.5">
                Last available snapshot: <span class="font-mono text-slate-200">{status.latest_backup.filename}</span>
                ({status.latest_backup.relative_time} • {status.latest_backup.size_formatted})
              </p>
            {/if}
          </div>
        </div>

        <div>
          <button
            type="button"
            onclick={() => handleTriggerBackup(false)}
            disabled={isTriggering}
            class="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-amber-500/20 hover:bg-amber-500/30 border border-amber-400/40 text-amber-200 transition-all cursor-pointer shadow-md disabled:opacity-50"
          >
            <Play class="w-4 h-4 text-amber-300" />
            <span>Trigger Backup Now</span>
          </button>
        </div>
      </aside>
    {/if}

    <!-- 4-Column Metric Summary Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card 1: Today Status -->
      <div class="bg-[#162036]/80 border border-white/[0.08] rounded-2xl p-4 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-medium uppercase tracking-wider">Today's Status</span>
          <Calendar class="w-4 h-4 text-slate-400" />
        </div>
        <div>
          <div class="text-lg font-bold flex items-center gap-2">
            {#if status.today_done}
              <span class="text-emerald-400">Completed</span>
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            {:else}
              <span class="text-amber-400">Pending</span>
              <span class="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></span>
            {/if}
          </div>
          <span class="text-[11px] text-slate-400">{status.today_date}</span>
        </div>
      </div>

      <!-- Card 2: Total Snapshots -->
      <div class="bg-[#162036]/80 border border-white/[0.08] rounded-2xl p-4 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-medium uppercase tracking-wider">Local Snapshots</span>
          <Archive class="w-4 h-4 text-slate-400" />
        </div>
        <div>
          <div class="text-lg font-bold text-white">
            {status.total_backups} <span class="text-xs font-normal text-slate-400">archives</span>
          </div>
          <span class="text-[11px] text-slate-400">Retention: {status.retention_days_local || 14} days local</span>
        </div>
      </div>

      <!-- Card 3: Storage Pool -->
      <div class="bg-[#162036]/80 border border-white/[0.08] rounded-2xl p-4 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-medium uppercase tracking-wider">Backup Size</span>
          <HardDrive class="w-4 h-4 text-slate-400" />
        </div>
        <div>
          <div class="text-lg font-bold text-white">
            {status.total_size_formatted}
          </div>
          <span class="text-[11px] text-slate-400 font-mono truncate block" title={status.backup_dir}>
            {status.backup_dir}
          </span>
        </div>
      </div>

      <!-- Card 4: Cloud Remote -->
      <div class="bg-[#162036]/80 border border-white/[0.08] rounded-2xl p-4 flex flex-col justify-between">
        <div class="flex items-center justify-between text-slate-400 mb-2">
          <span class="text-xs font-medium uppercase tracking-wider">Cloud Storage</span>
          <Cloud class="w-4 h-4 text-slate-400" />
        </div>
        <div>
          <div class="text-base font-bold text-white font-mono truncate" title={status.rclone_remote}>
            {status.rclone_remote}
          </div>
          <span class="text-[11px] text-slate-400">Google Drive Crypt • {status.retention_days_cloud || 60}d</span>
        </div>
      </div>
    </div>

    <!-- Snapshot Archive Inventory Table -->
    <div class="bg-[#162036]/80 border border-white/[0.08] rounded-2xl p-5 flex flex-col gap-4">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div class="flex items-center gap-2">
          <FileArchive class="w-4 h-4 text-sky-400" />
          <h3 class="text-sm font-semibold text-white">Snapshot Inventory</h3>
          <span class="text-xs text-slate-400">({status.total_backups} total)</span>
        </div>

        {#if status.backups.length > 5}
          <div class="w-full sm:w-64">
            <input
              type="text"
              placeholder="Search snapshots..."
              bind:value={searchQuery}
              class="w-full px-3 py-1.5 rounded-lg text-xs bg-black/40 border border-white/[0.1] text-white placeholder-slate-500 focus:outline-none focus:border-sky-400"
            />
          </div>
        {/if}
      </div>

      {#if status.backups.length === 0}
        <div class="py-8 text-center text-slate-400 text-xs">
          <Archive class="w-8 h-8 text-slate-600 mx-auto mb-2" />
          <p>No backup snapshots found in <span class="font-mono text-slate-300">{status.backup_dir}</span>.</p>
          <p class="mt-1 text-slate-500">Run a manual backup or wait for scheduled cron to generate the first snapshot.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-white/[0.08] text-slate-400">
                <th class="py-2.5 px-3 font-semibold">Snapshot Archive</th>
                <th class="py-2.5 px-3 font-semibold">Creation Date</th>
                <th class="py-2.5 px-3 font-semibold">Size</th>
                <th class="py-2.5 px-3 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              {#each filteredBackups as backup}
                <tr class="hover:bg-white/[0.02] transition-colors {backup.is_today ? 'bg-emerald-500/[0.03]' : ''}">
                  <td class="py-3 px-3">
                    <div class="flex items-center gap-2.5">
                      <FileArchive class="w-4 h-4 {backup.is_today ? 'text-emerald-400' : 'text-slate-400'} flex-shrink-0" />
                      <div>
                        <span class="font-mono font-medium text-slate-200 block truncate max-w-xs sm:max-w-md">
                          {backup.filename}
                        </span>
                        <span class="text-[10px] text-slate-400">
                          {backup.relative_time}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td class="py-3 px-3 text-slate-300 font-mono">
                    {backup.date}
                  </td>
                  <td class="py-3 px-3">
                    <span class="font-semibold text-white font-mono bg-white/[0.06] px-2 py-0.5 rounded text-[11px]">
                      {backup.size_formatted}
                    </span>
                  </td>
                  <td class="py-3 px-3 text-right">
                    {#if backup.is_today}
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Today
                      </span>
                    {:else}
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-white/[0.06] text-slate-300">
                        {backup.relative_time}
                      </span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {:else}
    <!-- Loading placeholder -->
    <div class="bg-[#162036]/80 border border-white/[0.08] rounded-2xl p-6 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
      <RotateCw class="w-4 h-4 animate-spin text-sky-400" />
      <span>Loading backup status...</span>
    </div>
  {/if}
</section>
