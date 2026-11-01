<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { Check, AlertTriangle, Info } from '@lucide/svelte';
</script>

<div class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm pointer-events-none" aria-live="polite">
  {#each store.toasts as toast (toast.id)}
    <div
      class="pointer-events-auto flex items-center gap-3 px-4 py-3.5 rounded-xl border shadow-xl text-sm transition-all duration-300 animate-in slide-in-from-bottom-2
      {toast.type === 'success' ? 'bg-[#064e3b] border-emerald-500/40 text-emerald-100' : ''}
      {toast.type === 'error' ? 'bg-[#881337] border-rose-500/40 text-rose-100' : ''}
      {toast.type === 'info' ? 'bg-[#0c4a6e] border-sky-500/40 text-sky-100' : ''}"
    >
      <span class="flex-shrink-0">
        {#if toast.type === 'success'}
          <Check class="w-4 h-4 text-emerald-300" />
        {:else if toast.type === 'error'}
          <AlertTriangle class="w-4 h-4 text-rose-300" />
        {:else}
          <Info class="w-4 h-4 text-sky-300" />
        {/if}
      </span>
      <span class="leading-snug">{toast.message}</span>
    </div>
  {/each}
</div>
