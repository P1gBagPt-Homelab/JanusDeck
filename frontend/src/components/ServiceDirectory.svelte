<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { fetchServices } from '../lib/api';
  import {
    Server,
    Shield,
    BookOpen,
    Activity,
    Globe,
    Copy,
    ExternalLink,
    RotateCw,
    Check
  } from '@lucide/svelte';

  let copiedUrl = $state<string | null>(null);

  // Group services by category
  const categories = $derived.by(() => {
    const map: Record<string, typeof store.services> = {};
    for (const item of store.services) {
      const cat = (item as any).category || 'Infrastructure & Platform';
      if (!map[cat]) map[cat] = [];
      map[cat].push(item);
    }
    return map;
  });

  async function refreshHealth() {
    store.isCheckingServices = true;
    try {
      const res = await fetchServices();
      store.services = res.services;
      store.addToast('Service health checks updated', 'success');
    } catch {
      store.addToast('Failed to check services availability', 'error');
    } finally {
      store.isCheckingServices = false;
    }
  }

  function copyToClipboard(url: string, e: MouseEvent) {
    e.stopPropagation();
    navigator.clipboard.writeText(url).then(() => {
      copiedUrl = url;
      store.addToast('Service link copied to clipboard', 'info', 2000);
      setTimeout(() => {
        if (copiedUrl === url) copiedUrl = null;
      }, 2000);
    });
  }

  function getIconComponent(iconName?: string) {
    switch (iconName?.toLowerCase()) {
      case 'server': return Server;
      case 'shield': return Shield;
      case 'book-open': return BookOpen;
      case 'activity': return Activity;
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
            {@const isOnline = svc.online === true}
            {@const latency = svc.response_time_ms ? `${Math.round(svc.response_time_ms)}ms` : null}
            {@const targetUrl = svc.url || svc.external_url || '#'}

            <div
              onclick={() => window.open(targetUrl, '_blank', 'noopener')}
              class="flex items-center justify-between p-4 bg-[#111827] hover:bg-[#162036] border border-white/[0.08] hover:border-sky-400/35 rounded-2xl shadow-sm transition-all cursor-pointer min-h-[84px] group"
              role="button"
              tabindex="0"
              onkeydown={(e) => e.key === 'Enter' && window.open(targetUrl, '_blank', 'noopener')}
            >
              <div class="flex items-center gap-3.5 min-w-0 flex-1">
                <div class="w-11 h-11 rounded-xl bg-sky-500/10 border border-sky-400/30 text-sky-400 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                  <Icon class="w-5 h-5" />
                </div>
                <div class="min-w-0 flex flex-col gap-0.5">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-semibold text-white truncate">{svc.name}</span>
                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold
                      {isOnline ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300' : 'bg-rose-500/15 border border-rose-500/30 text-rose-300'}">
                      <span class="w-1.5 h-1.5 rounded-full {isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}"></span>
                      <span>{isOnline ? (latency || 'Online') : 'Offline'}</span>
                    </span>
                  </div>
                  <span class="text-xs text-slate-400 truncate">{svc.description || svc.url}</span>
                </div>
              </div>

              <!-- Action buttons -->
              <div class="flex items-center gap-1.5 flex-shrink-0 ml-2">
                <button
                  type="button"
                  onclick={(e) => copyToClipboard(targetUrl, e)}
                  class="w-9 h-9 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 flex items-center justify-center transition-colors cursor-pointer"
                  title="Copy URL"
                  aria-label="Copy URL"
                >
                  {#if copiedUrl === targetUrl}
                    <Check class="w-4 h-4 text-emerald-400" />
                  {:else}
                    <Copy class="w-4 h-4" />
                  {/if}
                </button>
                <a
                  href={targetUrl}
                  target="_blank"
                  rel="noopener"
                  class="w-9 h-9 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] border border-white/[0.08] text-slate-300 flex items-center justify-center transition-colors"
                  title="Open Link"
                  aria-label="Open in new tab"
                >
                  <ExternalLink class="w-4 h-4" />
                </a>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {:else}
    <div class="text-center py-10 text-slate-400 text-sm">
      Loading homelab service directory...
    </div>
  {/if}
</section>
