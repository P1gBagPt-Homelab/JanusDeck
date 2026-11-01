<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { fetchServices, normalizeServices } from '../lib/api';
  import type { ServiceItem } from '../types/config';
  import {
    Server,
    Shield,
    BookOpen,
    Activity,
    Globe,
    Copy,
    ExternalLink,
    RotateCw,
    Check,
    Cpu,
    Database,
    HardDrive,
    Terminal,
    Network,
    Cloud,
    Lock,
    Boxes,
    Gauge
  } from '@lucide/svelte';

  let copiedUrl = $state<string | null>(null);

  // Group services by category
  const categories = $derived.by(() => {
    const map: Record<string, ServiceItem[]> = {};
    const items = normalizeServices(store.services);
    for (const item of items) {
      const cat = item.category || 'Infrastructure & Platform';
      if (!map[cat]) map[cat] = [];
      map[cat].push(item);
    }
    return map;
  });

  async function refreshHealth() {
    store.isCheckingServices = true;
    try {
      const res = await fetchServices();
      store.services = normalizeServices(res.services);
      store.addToast('Service health checks updated', 'success');
    } catch {
      store.addToast('Failed to check services availability', 'error');
    } finally {
      store.isCheckingServices = false;
    }
  }

  function handleOpen(url?: string) {
    if (!url || url === '#') {
      store.addToast('No destination URL configured for this service', 'error', 2500);
      return;
    }
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function copyToClipboard(url: string, e: MouseEvent) {
    e.stopPropagation();
    if (!url || url === '#') {
      store.addToast('No URL to copy', 'error', 2000);
      return;
    }
    navigator.clipboard.writeText(url).then(() => {
      copiedUrl = url;
      store.addToast('Service link copied to clipboard', 'info', 2000);
      setTimeout(() => {
        if (copiedUrl === url) copiedUrl = null;
      }, 2000);
    }).catch(() => {
      store.addToast('Could not copy link to clipboard', 'error', 2000);
    });
  }

  function getIconComponent(iconName?: string) {
    const cleaned = iconName?.toLowerCase().replace(/[-_\s]/g, '');
    switch (cleaned) {
      case 'server': return Server;
      case 'shield': return Shield;
      case 'bookopen':
      case 'book': return BookOpen;
      case 'activity':
      case 'pulse': return Activity;
      case 'cpu':
      case 'processor': return Cpu;
      case 'harddrive':
      case 'storage':
      case 'disk': return HardDrive;
      case 'database': return Database;
      case 'terminal':
      case 'console': return Terminal;
      case 'network':
      case 'wifi': return Network;
      case 'cloud': return Cloud;
      case 'lock': return Lock;
      case 'boxes':
      case 'docker':
      case 'container': return Boxes;
      case 'gauge':
      case 'monitoring': return Gauge;
      default: return Globe;
    }
  }
</script>

<section aria-labelledby="services-heading" class="flex flex-col gap-4">
  <div class="flex items-center justify-between">
    <h2 id="services-heading" class="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
      <Server class="w-5 h-5 text-sky-400" />
      <span>Service Directory</span>
    </h2>
    <button
      type="button"
      onclick={refreshHealth}
      class="w-9 h-9 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 flex items-center justify-center transition-all cursor-pointer"
      title="Refresh Health Checks"
      aria-label="Refresh service health checks"
    >
      <RotateCw class="w-4 h-4 {store.isCheckingServices ? 'animate-spin text-sky-400' : ''}" />
    </button>
  </div>

  {#if Object.keys(categories).length > 0}
    {#each Object.entries(categories) as [categoryName, items]}
      <div class="flex flex-col gap-3">
        <h3 class="text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-white/[0.08] pb-1.5 flex items-center gap-2">
          <span>{categoryName}</span>
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each items as svc}
            {@const Icon = getIconComponent(svc.icon)}
            {@const isOnline = svc.online === true || svc.status === 'online'}
            {@const isDegraded = svc.status === 'degraded'}
            {@const hasChecked = svc.status !== undefined || svc.online !== undefined}
            {@const latencyVal = svc.response_time_ms ?? svc.latency_ms}
            {@const latency = latencyVal != null ? `${Math.round(latencyVal)}ms` : null}
            {@const targetUrl = svc.url || svc.external_url || ''}

            <div
              onclick={() => handleOpen(targetUrl)}
              class="flex items-center justify-between p-4 bg-[#111827] hover:bg-[#162036] border border-white/[0.08] hover:border-sky-400/35 rounded-2xl shadow-sm transition-all cursor-pointer min-h-[84px] group"
              role="button"
              tabindex="0"
              onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && handleOpen(targetUrl)}
            >
              <div class="flex items-center gap-3.5 min-w-0 flex-1">
                <div class="w-11 h-11 rounded-xl bg-sky-500/10 border border-sky-400/30 text-sky-400 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                  <Icon class="w-5 h-5" />
                </div>
                <div class="min-w-0 flex flex-col gap-0.5">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-sm font-semibold text-white truncate">{svc.name}</span>
                    {#if isOnline}
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>{latency || 'Online'}</span>
                      </span>
                    {:else if isDegraded}
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/15 border border-amber-500/30 text-amber-300" title={svc.error || `HTTP ${svc.status_code}`}>
                        <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                        <span>Degraded{svc.status_code ? ` (${svc.status_code})` : ''}</span>
                      </span>
                    {:else if hasChecked}
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/15 border border-rose-500/30 text-rose-300" title={svc.error || 'Host unreachable'}>
                        <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                        <span>Offline</span>
                      </span>
                    {:else}
                      <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-500/15 border border-slate-500/30 text-slate-400">
                        <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse"></span>
                        <span>Checking...</span>
                      </span>
                    {/if}
                  </div>
                  {#if svc.description}
                    <span class="text-xs text-slate-400 truncate">{svc.description}</span>
                  {/if}
                  {#if targetUrl}
                    <span class="text-[11px] font-mono text-slate-500 truncate group-hover:text-sky-400/80 transition-colors">{targetUrl}</span>
                  {/if}
                </div>
              </div>

              <!-- Action buttons -->
              <div class="flex items-center gap-1.5 flex-shrink-0 ml-2">
                <button
                  type="button"
                  onclick={(e) => copyToClipboard(targetUrl, e)}
                  class="w-9 h-9 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 flex items-center justify-center transition-colors cursor-pointer"
                  title={targetUrl ? `Copy URL: ${targetUrl}` : 'Copy URL'}
                  aria-label="Copy URL"
                >
                  {#if copiedUrl === targetUrl && targetUrl}
                    <Check class="w-4 h-4 text-emerald-400" />
                  {:else}
                    <Copy class="w-4 h-4" />
                  {/if}
                </button>
                {#if targetUrl && targetUrl !== '#'}
                  <a
                    href={targetUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onclick={(e) => e.stopPropagation()}
                    class="w-9 h-9 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 flex items-center justify-center transition-colors"
                    title="Open Link in new tab"
                    aria-label="Open in new tab"
                  >
                    <ExternalLink class="w-4 h-4" />
                  </a>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {:else if store.config === null}
    <div class="text-center py-10 text-slate-400 text-sm">
      Loading homelab service directory...
    </div>
  {:else}
    <div class="text-center py-10 text-slate-400 text-sm bg-white/[0.02] border border-white/[0.05] rounded-2xl">
      No services configured. Add items to <code class="text-sky-400">services</code> in <code class="text-slate-300">config.yaml</code>.
    </div>
  {/if}
</section>
