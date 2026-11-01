<script lang="ts">
  import { onMount } from 'svelte';
  import { store } from '../lib/stores.svelte';
  import { createService, updateService } from '../lib/api';
  import type { ServiceItem } from '../types/config';
  import {
    Server,
    Shield,
    BookOpen,
    Activity,
    Globe,
    Cpu,
    Database,
    HardDrive,
    Terminal,
    Network,
    Cloud,
    Lock,
    Boxes,
    Gauge,
    X,
    Save,
    Plus,
    Check
  } from '@lucide/svelte';

  let {
    open = false,
    service = null,
    categories = [],
    onclose,
    onsaved
  }: {
    open: boolean;
    service: ServiceItem | null;
    categories: string[];
    onclose: () => void;
    onsaved: () => void;
  } = $props();

  const AVAILABLE_ICONS = [
    { id: 'server', label: 'Server', icon: Server },
    { id: 'shield', label: 'Shield', icon: Shield },
    { id: 'book-open', label: 'Wiki / Docs', icon: BookOpen },
    { id: 'activity', label: 'Activity', icon: Activity },
    { id: 'database', label: 'Database', icon: Database },
    { id: 'lock', label: 'Vault / Security', icon: Lock },
    { id: 'boxes', label: 'Docker / App', icon: Boxes },
    { id: 'cloud', label: 'Cloud', icon: Cloud },
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'network', label: 'Network', icon: Network },
    { id: 'cpu', label: 'Hardware', icon: Cpu },
    { id: 'hard-drive', label: 'Storage', icon: HardDrive },
    { id: 'gauge', label: 'Monitoring', icon: Gauge },
    { id: 'globe', label: 'Web / Other', icon: Globe },
  ];

  let name = $state('');
  let category = $state('');
  let url = $state('');
  let externalUrl = $state('');
  let healthCheckUrl = $state('');
  let icon = $state('globe');
  let description = $state('');
  let isSubmitting = $state(false);
  let errorMessage = $state<string | null>(null);

  // Sync state when editing a service or opening modal
  $effect(() => {
    if (open) {
      errorMessage = null;
      if (service) {
        name = service.name || '';
        category = service.category || 'Infrastructure & Platform';
        url = service.url || '';
        externalUrl = service.external_url || '';
        healthCheckUrl = service.health_check_url || '';
        icon = service.icon || 'globe';
        description = service.description || '';
      } else {
        name = '';
        category = categories[0] || 'Infrastructure & Platform';
        url = '';
        externalUrl = '';
        healthCheckUrl = '';
        icon = 'server';
        description = '';
      }
    }
  });

  function getIconComponent(iconName: string) {
    const item = AVAILABLE_ICONS.find(i => i.id === iconName);
    return item ? item.icon : Globe;
  }

  const PreviewIcon = $derived(getIconComponent(icon));

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    errorMessage = null;

    if (!name.trim()) {
      errorMessage = 'Service name is required.';
      return;
    }
    if (!category.trim()) {
      errorMessage = 'Category is required.';
      return;
    }
    if (!url.trim()) {
      errorMessage = 'Primary URL is required.';
      return;
    }

    isSubmitting = true;
    try {
      const payload: Partial<ServiceItem> = {
        name: name.trim(),
        category: category.trim(),
        url: url.trim(),
        external_url: externalUrl.trim() || undefined,
        health_check_url: healthCheckUrl.trim() || undefined,
        icon: icon || 'globe',
        description: description.trim() || undefined,
      };

      if (service && service.id) {
        await updateService(service.id, payload);
        store.addToast(`Updated service "${name}"`, 'success');
      } else {
        await createService(payload);
        store.addToast(`Added service "${name}" to directory`, 'success');
      }
      onsaved();
      onclose();
    } catch (err: any) {
      errorMessage = err.message || 'Failed to save service.';
    } finally {
      isSubmitting = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && open) {
      onclose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto"
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
  >
    <div
      class="bg-[#0f172a] border border-white/[0.1] rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden my-8"
      role="document"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-sky-500/10 border border-sky-400/30 text-sky-400 flex items-center justify-center">
            {#if service}
              <Save class="w-4 h-4" />
            {:else}
              <Plus class="w-4 h-4" />
            {/if}
          </div>
          <div>
            <h3 id="modal-title" class="text-base font-semibold text-white">
              {service ? 'Edit Homelab Service' : 'Add New Homelab Service'}
            </h3>
            <p class="text-xs text-slate-400">
              {service ? 'Update service connection endpoints and metadata' : 'Register a new service in PostgreSQL directory'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onclick={onclose}
          class="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white flex items-center justify-center transition-colors"
          aria-label="Close modal"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Form Body -->
      <form onsubmit={handleSubmit} class="p-6 flex flex-col gap-5">
        {#if errorMessage}
          <div class="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs">
            {errorMessage}
          </div>
        {/if}

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Name -->
          <div class="flex flex-col gap-1.5">
            <label for="svc-name" class="text-xs font-semibold text-slate-300">
              Service Name <span class="text-rose-400">*</span>
            </label>
            <input
              id="svc-name"
              type="text"
              bind:value={name}
              placeholder="e.g. Vaultwarden"
              required
              class="w-full px-3 py-2 bg-black/40 border border-white/[0.1] rounded-xl text-white text-sm focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all placeholder:text-slate-600"
            />
          </div>

          <!-- Category -->
          <div class="flex flex-col gap-1.5">
            <label for="svc-category" class="text-xs font-semibold text-slate-300">
              Category <span class="text-rose-400">*</span>
            </label>
            <input
              id="svc-category"
              type="text"
              list="category-suggestions"
              bind:value={category}
              placeholder="e.g. Security & Passwords"
              required
              class="w-full px-3 py-2 bg-black/40 border border-white/[0.1] rounded-xl text-white text-sm focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all placeholder:text-slate-600"
            />
            <datalist id="category-suggestions">
              {#each categories as cat}
                <option value={cat}>{cat}</option>
              {/each}
              <option value="Infrastructure & Platform">Infrastructure & Platform</option>
              <option value="Monitoring & Knowledge">Monitoring & Knowledge</option>
              <option value="Media & Streaming">Media & Streaming</option>
              <option value="Smart Home & IoT">Smart Home & IoT</option>
            </datalist>
          </div>
        </div>

        <!-- Primary URL -->
        <div class="flex flex-col gap-1.5">
          <label for="svc-url" class="text-xs font-semibold text-slate-300">
            Internal / Primary URL <span class="text-rose-400">*</span>
          </label>
          <input
            id="svc-url"
            type="url"
            bind:value={url}
            placeholder="http://192.168.1.68:8080"
            required
            class="w-full px-3 py-2 bg-black/40 border border-white/[0.1] rounded-xl text-white font-mono text-sm focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all placeholder:text-slate-600"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- External / WireGuard URL -->
          <div class="flex flex-col gap-1.5">
            <label for="svc-ext-url" class="text-xs font-semibold text-slate-300">
              External / Public URL <span class="text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              id="svc-ext-url"
              type="url"
              bind:value={externalUrl}
              placeholder="https://vault.janus-lab.duckdns.org"
              class="w-full px-3 py-2 bg-black/40 border border-white/[0.1] rounded-xl text-white font-mono text-sm focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all placeholder:text-slate-600"
            />
          </div>

          <!-- Health Check URL -->
          <div class="flex flex-col gap-1.5">
            <label for="svc-health-url" class="text-xs font-semibold text-slate-300">
              Health Probe URL <span class="text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              id="svc-health-url"
              type="url"
              bind:value={healthCheckUrl}
              placeholder="Defaults to Primary URL"
              class="w-full px-3 py-2 bg-black/40 border border-white/[0.1] rounded-xl text-white font-mono text-sm focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all placeholder:text-slate-600"
            />
          </div>
        </div>

        <!-- Description -->
        <div class="flex flex-col gap-1.5">
          <label for="svc-desc" class="text-xs font-semibold text-slate-300">
            Description <span class="text-slate-500 font-normal">(optional)</span>
          </label>
          <input
            id="svc-desc"
            type="text"
            bind:value={description}
            placeholder="e.g. Encrypted Bitwarden-compatible password vault"
            class="w-full px-3 py-2 bg-black/40 border border-white/[0.1] rounded-xl text-white text-sm focus:outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400 transition-all placeholder:text-slate-600"
          />
        </div>

        <!-- Icon Selector -->
        <div class="flex flex-col gap-2">
          <span class="text-xs font-semibold text-slate-300">
            Choose Icon
          </span>
          <div class="grid grid-cols-7 gap-2">
            {#each AVAILABLE_ICONS as item}
              {@const IconComp = item.icon}
              {@const isSelected = icon === item.id}
              <button
                type="button"
                onclick={() => icon = item.id}
                class="flex flex-col items-center justify-center p-2.5 rounded-xl border transition-all cursor-pointer {isSelected ? 'bg-sky-500/20 border-sky-400 text-sky-300 ring-2 ring-sky-400/30' : 'bg-black/30 border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.05]'}"
                title={item.label}
              >
                <IconComp class="w-5 h-5" />
              </button>
            {/each}
          </div>
        </div>

        <!-- Live Preview -->
        <div class="flex flex-col gap-1.5 pt-2 border-t border-white/[0.08]">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Preview</span>
          <div class="flex items-center justify-between p-3.5 bg-[#111827] border border-white/[0.08] rounded-xl">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-400/30 text-sky-400 flex items-center justify-center flex-shrink-0">
                <PreviewIcon class="w-5 h-5" />
              </div>
              <div class="min-w-0 flex flex-col gap-0.5">
                <span class="text-sm font-semibold text-white truncate">{name || 'Service Name'}</span>
                <span class="text-xs text-slate-400 truncate">{description || 'Service description will appear here'}</span>
                <span class="text-[11px] font-mono text-slate-500 truncate">{url || 'http://192.168.1.68:...'}</span>
              </div>
            </div>
            <div class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex-shrink-0 ml-2">
              Ready
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center justify-end gap-3 pt-4 border-t border-white/[0.08]">
          <button
            type="button"
            onclick={onclose}
            disabled={isSubmitting}
            class="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            class="px-5 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white text-xs font-semibold shadow-lg shadow-sky-500/25 flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            {#if isSubmitting}
              <div class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <span>Saving...</span>
            {:else}
              <Check class="w-3.5 h-3.5" />
              <span>{service ? 'Save Changes' : 'Create Service'}</span>
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
