<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { verifyPin } from '../lib/api';
  import { Lock, X, Check } from '@lucide/svelte';

  let pinBuffer = $state('');
  let isSubmitting = $state(false);
  let lockoutRemaining = $state(0);
  let lockoutInterval: ReturnType<typeof setInterval> | null = null;

  function closeModal() {
    pinBuffer = '';
    store.activeModal = 'none';
    store.pendingAction = null;
  }

  function handleDigit(digit: string) {
    if (pinBuffer.length >= 32) return;
    pinBuffer += digit;
  }

  function handleBackspace() {
    if (pinBuffer.length > 0) {
      pinBuffer = pinBuffer.slice(0, -1);
    }
  }

  function handleClear() {
    pinBuffer = '';
  }

  async function submitPin() {
    if (pinBuffer.length === 0 || isSubmitting) return;

    isSubmitting = true;
    try {
      const res = await verifyPin(pinBuffer);
      if (res.session_token) {
        store.setSession(res.session_token);
        store.addToast('Master PIN authorized', 'success');
      }

      if (store.pendingAction?.type === 'unlock_only') {
        closeModal();
      } else {
        // Proceed to 5-second countdown gate
        store.activeModal = 'countdown';
      }
    } catch (err: any) {
      if (err.status === 429) {
        startLockout(err.lockout_remaining_seconds || 60);
      } else {
        store.addToast(err.message || 'Invalid PIN entered', 'error');
        pinBuffer = '';
      }
    } finally {
      isSubmitting = false;
    }
  }

  function startLockout(seconds: number) {
    lockoutRemaining = seconds;
    if (lockoutInterval) clearInterval(lockoutInterval);
    lockoutInterval = setInterval(() => {
      lockoutRemaining--;
      if (lockoutRemaining <= 0) {
        if (lockoutInterval) clearInterval(lockoutInterval);
        lockoutInterval = null;
      }
    }, 1000);
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (store.activeModal !== 'pin') return;

    if (e.key === 'Escape') {
      closeModal();
    } else if (/^[0-9]$/.test(e.key)) {
      handleDigit(e.key);
    } else if (e.key === 'Backspace') {
      handleBackspace();
    } else if (e.key === 'Delete' || e.key.toLowerCase() === 'c') {
      handleClear();
    } else if (e.key === 'Enter') {
      submitPin();
    }
  }

  const displayDotsCount = $derived(Math.max(4, pinBuffer.length));
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if store.activeModal === 'pin'}
  <div
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
    role="dialog"
    aria-modal="true"
    aria-labelledby="pin-modal-title"
  >
    <div class="w-full max-w-sm bg-[#111827] border border-white/[0.16] rounded-3xl p-6 shadow-2xl flex flex-col gap-5">
      <!-- Modal Header -->
      <div class="flex items-center justify-between">
        <h2 id="pin-modal-title" class="text-base font-bold text-white flex items-center gap-2">
          <Lock class="w-5 h-5 text-sky-400" />
          <span>Security Verification</span>
        </h2>
        <button
          type="button"
          onclick={closeModal}
          class="p-1 text-slate-400 hover:text-white rounded-lg transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Masked Dots Display -->
      <div class="flex flex-col items-center gap-3">
        <p class="text-xs text-slate-400 text-center">
          Enter master PIN to authorize: <span class="text-sky-300 font-semibold">{store.pendingAction?.label || 'Host Action'}</span>
        </p>

        <div class="flex items-center justify-center gap-2 min-h-[36px] flex-wrap max-w-[280px]">
          {#each Array(displayDotsCount) as _, idx}
            <div
              class="w-3.5 h-3.5 rounded-full border-2 transition-all duration-150
              {idx < pinBuffer.length ? 'bg-sky-400 border-sky-400' : 'border-white/20 bg-transparent'}"
            ></div>
          {/each}
        </div>
      </div>

      <!-- Lockout Alert Banner -->
      {#if lockoutRemaining > 0}
        <div class="bg-rose-950/80 border border-rose-500/40 rounded-xl p-3 text-xs text-rose-200 text-center tabular-nums">
          Security lockout active. Try again in {lockoutRemaining}s.
        </div>
      {/if}

      <!-- Numeric Keypad Grid -->
      <div class="grid grid-cols-3 gap-2.5 w-full">
        {#each [1, 2, 3, 4, 5, 6, 7, 8, 9] as num}
          <button
            type="button"
            onclick={() => handleDigit(num.toString())}
            class="h-14 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] active:scale-95 border border-white/[0.08] text-white text-xl font-bold font-mono transition-all cursor-pointer flex items-center justify-center select-none"
          >
            {num}
          </button>
        {/each}

        <button
          type="button"
          onclick={handleClear}
          class="h-14 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] active:scale-95 border border-white/[0.08] text-slate-400 hover:text-white text-sm font-semibold transition-all cursor-pointer flex items-center justify-center select-none"
          aria-label="Clear PIN"
        >
          C
        </button>

        <button
          type="button"
          onclick={() => handleDigit('0')}
          class="h-14 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] active:scale-95 border border-white/[0.08] text-white text-xl font-bold font-mono transition-all cursor-pointer flex items-center justify-center select-none"
        >
          0
        </button>

        <button
          type="button"
          onclick={handleBackspace}
          class="h-14 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] active:scale-95 border border-white/[0.08] text-slate-400 hover:text-white text-sm font-semibold transition-all cursor-pointer flex items-center justify-center select-none"
          aria-label="Backspace"
        >
          ⌫
        </button>
      </div>

      <!-- Submit PIN Button -->
      <button
        type="button"
        onclick={submitPin}
        disabled={pinBuffer.length === 0 || isSubmitting || lockoutRemaining > 0}
        class="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-bold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-all cursor-pointer shadow-sm min-h-[48px]"
      >
        <span>Authorize Action</span>
        <Check class="w-4 h-4" />
      </button>
    </div>
  </div>
{/if}
