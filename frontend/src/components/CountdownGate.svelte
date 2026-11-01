<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { executePowerAction, fetchPowerStatus } from '../lib/api';
  import { AlertTriangle, RotateCw, CheckCircle2 } from '@lucide/svelte';

  let countdown = $state(5);
  let timer: ReturnType<typeof setInterval> | null = null;
  let statusState = $state<'counting' | 'dispatching' | 'done' | 'aborted'>('counting');
  let statusMessage = $state('');

  const circumference = 2 * Math.PI * 44; // r=44
  const strokeOffset = $derived(circumference * (1 - countdown / 5));

  function startCountdown() {
    countdown = 5;
    statusState = 'counting';

    if (timer) clearInterval(timer);
    timer = setInterval(() => {
      countdown--;
      if (countdown <= 0) {
        if (timer) clearInterval(timer);
        timer = null;
        dispatchExecution();
      }
    }, 1000);
  }

  function abortAction() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    statusState = 'aborted';
    store.addToast('Power action aborted by user', 'info', 3000);
    setTimeout(closeGate, 600);
  }

  async function dispatchExecution() {
    if (!store.pendingAction) return;

    statusState = 'dispatching';
    try {
      const res = await executePowerAction(
        store.pendingAction.type as any,
        store.sessionToken,
        undefined,
        store.pendingAction.targetId
      );
      statusState = 'done';
      statusMessage = res.message || 'Power operation executed successfully.';
      store.addToast(statusMessage, 'success', 6000);

      // Refresh power status after execution
      fetchPowerStatus().then(st => store.powerStatus = st).catch(() => {});

      setTimeout(closeGate, 3000);
    } catch (err: any) {
      statusState = 'aborted';
      store.addToast(err.message || 'Operation failed to execute', 'error', 5000);
      setTimeout(closeGate, 2500);
    }
  }

  function closeGate() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    store.activeModal = 'none';
    store.pendingAction = null;
  }

  $effect(() => {
    if (store.activeModal === 'countdown') {
      startCountdown();
    }
  });

  function handleKeyDown(e: KeyboardEvent) {
    if (store.activeModal === 'countdown' && e.key === 'Escape') {
      abortAction();
    }
  }
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if store.activeModal === 'countdown'}
  <div
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
    role="dialog"
    aria-modal="true"
    aria-labelledby="countdown-modal-title"
  >
    <div class="w-full max-w-sm bg-[#111827] border border-white/[0.16] rounded-3xl p-6 shadow-2xl flex flex-col items-center text-center gap-5">
      <!-- Header -->
      <div class="flex items-center gap-2 text-rose-400">
        <AlertTriangle class="w-5 h-5" />
        <h2 id="countdown-modal-title" class="text-base font-bold text-white">Confirm Execution</h2>
      </div>

      {#if statusState === 'counting'}
        <!-- Animated 5s Circle -->
        <div class="relative w-28 h-28 my-1 flex items-center justify-center">
          <svg class="-rotate-90 w-full h-full" viewBox="0 0 100 100" aria-hidden="true">
            <circle cx="50" cy="50" r="44" class="fill-none stroke-white/[0.08]" stroke-width="6" />
            <circle
              cx="50"
              cy="50"
              r="44"
              class="fill-none stroke-rose-500 transition-[stroke-dashoffset] duration-1000 linear"
              stroke-width="6"
              stroke-linecap="round"
              stroke-dasharray={circumference}
              style="stroke-dashoffset: {strokeOffset}px;"
            />
          </svg>
          <div class="absolute inset-0 flex items-center justify-center text-4xl font-extrabold text-white font-mono tabular-nums">
            {countdown}
          </div>
        </div>

        <div>
          <h3 class="text-base font-bold text-white">{store.pendingAction?.label}</h3>
          <p class="text-xs text-slate-300 mt-1">
            Executing in <span class="font-bold text-white tabular-nums">{countdown}</span> seconds. Click below to cancel anytime.
          </p>
        </div>

        <button
          type="button"
          onclick={abortAction}
          class="w-full py-3.5 px-4 rounded-xl text-sm font-bold bg-[#1e1b4b] border-2 border-rose-500 text-rose-200 hover:bg-rose-600 hover:text-white transition-all cursor-pointer shadow-sm min-h-[48px]"
          aria-label="Abort this power operation immediately"
        >
          Abort Action
        </button>
      {:else if statusState === 'dispatching'}
        <div class="py-8 flex flex-col items-center gap-3">
          <RotateCw class="w-8 h-8 text-sky-400 animate-spin" />
          <h3 class="text-sm font-bold text-white">Dispatching signal to host...</h3>
        </div>
      {:else if statusState === 'done'}
        <div class="py-6 flex flex-col items-center gap-3">
          <CheckCircle2 class="w-10 h-10 text-emerald-400" />
          <h3 class="text-base font-bold text-white">Signal Dispatched</h3>
          <p class="text-xs text-slate-300">{statusMessage}</p>
        </div>
      {/if}
    </div>
  </div>
{/if}
