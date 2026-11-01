<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import CircularGauge from './CircularGauge.svelte';
  import { Activity, Cpu, MemoryStick, Monitor, HardDrive, Thermometer } from '@lucide/svelte';

  // CPU Derived
  const cpu = $derived(store.metrics?.cpu);
  const cpuLoad = $derived(cpu?.usage_percent ?? 0);
  const cpuFreqGhz = $derived(
    cpu?.frequency?.current_mhz
      ? (cpu.frequency.current_mhz > 100 ? (cpu.frequency.current_mhz / 1000).toFixed(2) : cpu.frequency.current_mhz.toFixed(2))
      : null
  );
  const cpuTemp = $derived(cpu?.temperature_c != null ? Math.round(cpu.temperature_c) : null);
  const cpuCores = $derived(cpu?.per_core_percent ?? []);

  // Memory Derived
  const mem = $derived(store.metrics?.memory);
  const memLoad = $derived(mem?.usage_percent ?? 0);
  const memUsedGb = $derived(mem?.used_gb?.toFixed(1) ?? '--');
  const memTotalGb = $derived(mem?.total_gb ? Math.round(mem.total_gb) : '--');
  const memSwapPct = $derived(mem?.swap?.usage_percent ? Math.round(mem.swap.usage_percent) : 0);

  // GPU Derived
  const gpu = $derived(store.metrics?.gpu);
  const gpuAvailable = $derived(gpu?.available === true);
  const gpuLoad = $derived(gpu?.usage_percent ?? 0);
  const gpuName = $derived(
    (gpu?.device_name || gpu?.label || 'RTX 2070').replace('NVIDIA GeForce ', '')
  );
  const gpuVramUsed = $derived(gpu?.vram?.used_gb != null ? gpu.vram.used_gb.toFixed(1) : '--');
  const gpuVramTotal = $derived(gpu?.vram?.total_gb != null ? Math.round(gpu.vram.total_gb) : '--');
  const gpuTemp = $derived(gpu?.temperature_c != null ? Math.round(gpu.temperature_c) : null);
  const gpuPowerWatts = $derived(gpu?.power_watts != null ? Math.round(gpu.power_watts) : null);

  // Storage Pools Derived
  const storagePools = $derived(store.metrics?.storage?.pools ?? []);
</script>

<section aria-labelledby="telemetry-heading" class="flex flex-col gap-4">
  <div class="flex items-center justify-between">
    <h2 id="telemetry-heading" class="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
      <Activity class="w-5 h-5 text-sky-400" />
      <span>Hardware Telemetry</span>
    </h2>
    <span class="text-xs text-slate-400 font-medium">Live NVML &amp; Kernel Stream</span>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- CPU Card -->
    <article class="bg-[#111827]/80 backdrop-blur-md border border-white/[0.08] hover:border-white/[0.18] rounded-2xl p-5 shadow-md transition-all flex flex-col justify-between gap-4 min-h-[220px]">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="text-sm font-semibold text-white">CPU Processor</h3>
          <span class="text-xs text-slate-400">{cpu?.label || 'Intel Core i7-8700K'}</span>
        </div>
        <div class="w-8 h-8 rounded-lg bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-slate-300">
          <Cpu class="w-4 h-4" />
        </div>
      </div>

      <CircularGauge
        value={cpuLoad}
        color={cpuLoad > 85 ? 'rose' : cpuLoad > 65 ? 'amber' : 'cyan'}
        unit="% LOAD"
      />

      <!-- Per-Core Visualizer Bars -->
      <div>
        <div class="flex justify-between text-[11px] text-slate-400 mb-1">
          <span>Per-Core Activity</span>
          <span class="tabular-nums">{cpuFreqGhz ? `${cpuFreqGhz} GHz` : '-- GHz'}</span>
        </div>
        <div class="grid grid-cols-6 gap-1 w-full" aria-label="Per-core load bars">
          {#each cpuCores.slice(0, 12) as corePct}
            {@const pct = Math.max(0, Math.min(100, Math.round(corePct)))}
            <div class="bg-white/[0.08] h-4 rounded-sm relative overflow-hidden" title="Core: {pct}%">
              <div
                class="absolute bottom-0 left-0 right-0 transition-all duration-300
                {pct > 80 ? 'bg-rose-500' : pct > 60 ? 'bg-amber-400' : 'bg-sky-400'}"
                style="height: {pct}%;"
              ></div>
            </div>
          {/each}
        </div>
      </div>

      <!-- CPU Meta Footer -->
      <div class="flex items-center justify-between pt-3 border-t border-white/[0.08] text-xs">
        <div class="flex flex-col">
          <span class="text-[11px] text-slate-400">Package Temp</span>
          {#if cpuTemp != null}
            <span class="inline-flex items-center gap-1 font-semibold text-xs
              {cpuTemp >= 80 ? 'text-rose-300' : cpuTemp >= 65 ? 'text-amber-300' : 'text-sky-300'}">
              <Thermometer class="w-3 h-3" />
              <span>{cpuTemp}°C</span>
            </span>
          {:else}
            <span class="text-slate-400">--°C</span>
          {/if}
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[11px] text-slate-400">Cores / Threads</span>
          <span class="font-semibold text-slate-200 tabular-nums">
            {cpu?.core_count_physical ?? 6}C / {cpu?.core_count_logical ?? 12}T
          </span>
        </div>
      </div>
    </article>

    <!-- Memory Card -->
    <article class="bg-[#111827]/80 backdrop-blur-md border border-white/[0.08] hover:border-white/[0.18] rounded-2xl p-5 shadow-md transition-all flex flex-col justify-between gap-4 min-h-[220px]">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="text-sm font-semibold text-white">DDR4 Memory</h3>
          <span class="text-xs text-slate-400">{mem?.label || 'Dual-Channel Pool'}</span>
        </div>
        <div class="w-8 h-8 rounded-lg bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-slate-300">
          <MemoryStick class="w-4 h-4" />
        </div>
      </div>

      <CircularGauge
        value={memLoad}
        color={memLoad > 90 ? 'rose' : memLoad > 75 ? 'amber' : 'indigo'}
        unit="% UTILIZED"
      />

      <div class="flex items-center justify-between pt-3 border-t border-white/[0.08] text-xs">
        <div class="flex flex-col">
          <span class="text-[11px] text-slate-400">Used / Total</span>
          <span class="font-semibold text-slate-200 tabular-nums">{memUsedGb} / {memTotalGb} GB</span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[11px] text-slate-400">Swap</span>
          <span class="font-semibold text-slate-200 tabular-nums">{memSwapPct}%</span>
        </div>
      </div>
    </article>

    <!-- GPU Card -->
    <article class="bg-[#111827]/80 backdrop-blur-md border border-white/[0.08] hover:border-white/[0.18] rounded-2xl p-5 shadow-md transition-all flex flex-col justify-between gap-4 min-h-[220px]">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="text-sm font-semibold text-white">{gpuName}</h3>
          <span class="text-xs text-slate-400">NVIDIA NVML</span>
        </div>
        <div class="w-8 h-8 rounded-lg bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-slate-300">
          <Monitor class="w-4 h-4" />
        </div>
      </div>

      <CircularGauge
        value={gpuAvailable ? gpuLoad : 0}
        color={gpuLoad > 85 ? 'rose' : gpuLoad > 60 ? 'amber' : 'emerald'}
        unit={gpuAvailable ? '% LOAD' : 'STANDBY'}
      />

      <div class="flex items-center justify-between pt-3 border-t border-white/[0.08] text-xs">
        <div class="flex flex-col">
          <span class="text-[11px] text-slate-400">VRAM Usage</span>
          <span class="font-semibold text-slate-200 tabular-nums">
            {gpuAvailable ? `${gpuVramUsed} / ${gpuVramTotal} GB` : 'Standby / NVML Off'}
          </span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[11px] text-slate-400">GPU Core</span>
          {#if gpuTemp != null}
            <span class="inline-flex items-center gap-1 font-semibold text-xs
              {gpuTemp >= 82 ? 'text-rose-300' : gpuTemp >= 70 ? 'text-amber-300' : 'text-sky-300'}">
              <Thermometer class="w-3 h-3" />
              <span>{gpuTemp}°C</span>
            </span>
          {:else if gpuPowerWatts != null}
            <span class="font-semibold text-slate-200 tabular-nums">{gpuPowerWatts}W</span>
          {:else}
            <span class="text-slate-400">--°C</span>
          {/if}
        </div>
      </div>
    </article>

    <!-- Storage Card -->
    <article class="bg-[#111827]/80 backdrop-blur-md border border-white/[0.08] hover:border-white/[0.18] rounded-2xl p-5 shadow-md transition-all flex flex-col justify-between gap-4 min-h-[220px]">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="text-sm font-semibold text-white">Storage Pools</h3>
          <span class="text-xs text-slate-400">LVM SSD &amp; Hard Disks</span>
        </div>
        <div class="w-8 h-8 rounded-lg bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-slate-300">
          <HardDrive class="w-4 h-4" />
        </div>
      </div>

      <!-- Pools Progress List -->
      <div class="flex flex-col gap-3 justify-center flex-1">
        {#if storagePools.length > 0}
          {#each storagePools as pool}
            {@const pct = Math.round(pool.usage_percent ?? 0)}
            {@const freeGb = pool.free_gb != null ? Math.round(pool.free_gb) : '--'}
            {@const totalGb = pool.total_gb != null ? Math.round(pool.total_gb) : '--'}
            {@const isWarn = pct > 85}
            <div class="flex flex-col gap-1.5">
              <div class="flex justify-between items-center text-xs">
                <span class="font-semibold text-slate-200 flex items-center gap-1.5 truncate max-w-[150px]">
                  <HardDrive class="w-3.5 h-3.5 text-sky-400 flex-shrink-0" />
                  <span class="truncate">{pool.name || pool.path}</span>
                </span>
                <span class="tabular-nums text-slate-300 text-[11px]">
                  {pct}% ({freeGb} GB free)
                </span>
              </div>
              <div class="h-2 rounded-full bg-white/[0.08] overflow-hidden relative">
                <div
                  class="h-full rounded-full transition-all duration-500
                  {isWarn ? 'bg-amber-400' : 'bg-sky-400'}"
                  style="width: {pct}%;"
                ></div>
              </div>
              <div class="flex justify-between text-[10px] text-slate-400 tabular-nums">
                <span>Used: {pool.used_gb != null ? `${pool.used_gb.toFixed(1)} GB` : '--'}</span>
                <span>Total: {totalGb} GB</span>
              </div>
            </div>
          {/each}
        {:else}
          <div class="text-xs text-slate-400 text-center py-4">Detecting disk partitions...</div>
        {/if}
      </div>

      <div class="flex items-center justify-between pt-3 border-t border-white/[0.08] text-xs">
        <div class="flex flex-col">
          <span class="text-[11px] text-slate-400">Health</span>
          <span class="font-semibold text-emerald-400">Optimal</span>
        </div>
        <div class="flex flex-col items-end">
          <span class="text-[11px] text-slate-400">Filesystem</span>
          <span class="font-semibold text-slate-200">ext4 / LVM</span>
        </div>
      </div>
    </article>
  </div>
</section>
