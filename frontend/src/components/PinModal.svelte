<script lang="ts">
  import { store } from '../lib/stores.svelte';
  import { verifyPin } from '../lib/api';
  import { Lock, X, Check, ClipboardPaste, Zap, ShieldAlert } from '@lucide/svelte';

  interface Props {
    mandatory?: boolean;
  }

  let { mandatory = false }: Props = $props();

  let pinBuffer = $state('');
  let isSubmitting = $state(false);
  let lockoutRemaining = $state(0);
  let lockoutInterval: ReturnType<typeof setInterval> | null = null;
  let pinInputRef: HTMLInputElement | null = $state(null);

  const isActive = $derived(mandatory ? !store.isUnlocked : store.activeModal === 'pin');

  $effect(() => {
    if (isActive) {
      setTimeout(() => {
        pinInputRef?.focus();
      }, 50);
    }
  });

  function closeModal() {
    if (mandatory) return;
    pinBuffer = '';
    if (pinInputRef) pinInputRef.value = '';
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
    if (pinInputRef) pinInputRef.value = '';
  }

  function applyPin(rawText: string) {
    if (lockoutRemaining > 0) return;
    const digits = rawText.replace(/\D/g, '');
    if (!digits) {
      store.addToast('No numeric PIN found in clipboard', 'error');
      return;
    }
    pinBuffer = digits.slice(0, 32);
    store.addToast('PIN pasted', 'info');
  }

  function handlePaste(e: ClipboardEvent) {
    if (!isActive) return;
    e.preventDefault();
    const text = e.clipboardData?.getData('text') || '';
    if (text) {
      applyPin(text);
    }
  }

  async function pasteFromClipboard() {
    if (!isActive || lockoutRemaining > 0) return;
    try {
      if (!navigator.clipboard?.readText) {
        store.addToast('Clipboard API not available. Press Ctrl+V or ⌘V to paste.', 'error');
        return;
      }
      const text = await navigator.clipboard.readText();
      if (!text || text.trim().length === 0) {
        store.addToast('Clipboard is empty', 'error');
        return;
      }
      applyPin(text);
    } catch {
      store.addToast('Clipboard access denied. Press Ctrl+V or ⌘V to paste.', 'error');
    }
  }

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.value) {
      applyPin(target.value);
      target.value = '';
    }
  }

  async function submitPin() {
    if (pinBuffer.length === 0 || isSubmitting) return;

    isSubmitting = true;
    try {
      const res = await verifyPin(pinBuffer);
      const token = res.session_token || 'authenticated';
      store.setSession(token, pinBuffer);
      store.addToast('Master PIN authorized', 'success');

      if (mandatory || store.pendingAction?.type === 'unlock_only' || !store.pendingAction) {
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
        if (pinInputRef) pinInputRef.value = '';
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
    if (!isActive) return;

    if (e.key === 'Escape') {
      e.preventDefault();
      if (!mandatory) {
        closeModal();
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      submitPin();
    } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'v') {
      // Allow browser native paste event to fire
      return;
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      handleBackspace();
    } else if (e.key === 'Delete' || (!e.ctrlKey && !e.metaKey && e.key.toLowerCase() === 'c')) {
      e.preventDefault();
      handleClear();
    } else if (/^[0-9]$/.test(e.key)) {
      e.preventDefault();
      handleDigit(e.key);
    }
  }

  const displayDotsCount = $derived(Math.max(4, pinBuffer.length));
</script>

<svelte:window onkeydown={handleKeyDown} onpaste={handlePaste} />

{#snippet pinCard()}
  <div class="w-full max-w-sm bg-[#111827] border border-white/[0.16] rounded-3xl p-6 shadow-2xl flex flex-col gap-5">
    <!-- Modal Header -->
    <div class="flex items-center justify-between">
      <h2 id="pin-modal-title" class="text-base font-bold text-white flex items-center gap-2">
        <Lock class="w-5 h-5 text-sky-400" />
        <span>Security Verification</span>
      </h2>
      {#if !mandatory}
        <button
          type="button"
          onclick={closeModal}
          class="p-1 text-slate-400 hover:text-white rounded-lg transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X class="w-5 h-5" />
        </button>
      {:else}
        <span class="text-[11px] font-semibold text-sky-400 bg-sky-500/10 border border-sky-400/30 px-2 py-0.5 rounded-full">
          Mandatory
        </span>
      {/if}
    </div>

    <!-- Hidden accessible input for paste / autofill / mobile compatibility -->
    <input
      bind:this={pinInputRef}
      type="password"
      inputmode="numeric"
      autocomplete="one-time-code"
      pattern="[0-9]*"
      aria-label="PIN Code"
      onpaste={handlePaste}
      oninput={handleInput}
      class="sr-only"
      tabindex="-1"
    />

    <!-- Masked Dots Display & Paste Shortcut -->
    <div class="flex flex-col items-center gap-3">
      <p class="text-xs text-slate-400 text-center">
        {#if mandatory}
          Enter master PIN to unlock and view command deck
        {:else}
          Enter master PIN to authorize: <span class="text-sky-300 font-semibold">{store.pendingAction?.label || 'Host Action'}</span>
        {/if}
      </p>

      <!-- Dots Display (clicking focuses the input) -->
      <button
        type="button"
        onclick={() => pinInputRef?.focus()}
        class="flex items-center justify-center gap-2 min-h-[36px] flex-wrap max-w-[280px] p-1.5 rounded-xl hover:bg-white/[0.04] transition-colors cursor-pointer"
        aria-label="Focus PIN input"
      >
        {#each Array(displayDotsCount) as _, idx}
          <div
            class="w-3.5 h-3.5 rounded-full border-2 transition-all duration-150
            {idx < pinBuffer.length ? 'bg-sky-400 border-sky-400' : 'border-white/20 bg-transparent'}"
          ></div>
        {/each}
      </button>

      <!-- Paste PIN Action Button -->
      <button
        type="button"
        onclick={pasteFromClipboard}
        disabled={lockoutRemaining > 0}
        class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium text-slate-300 hover:text-white bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] active:scale-95 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed select-none shadow-sm"
        title="Paste PIN from clipboard (⌘V / Ctrl+V)"
      >
        <ClipboardPaste class="w-3.5 h-3.5 text-sky-400" />
        <span>Paste PIN</span>
      </button>
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
      <span>{mandatory ? 'Unlock Website' : 'Authorize Action'}</span>
      <Check class="w-4 h-4" />
    </button>
  </div>
{/snippet}

{#if mandatory && isActive}
  <div class="min-h-screen w-full flex flex-col items-center justify-center p-4 sm:p-6 bg-[#0b0f19]">
    <!-- Brand badge at top -->
    <div class="flex flex-col items-center gap-2 mb-6 text-center animate-in fade-in duration-300">
      <div class="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-400/30 flex items-center justify-center text-sky-400 shadow-lg shadow-sky-500/10 mb-1">
        <Zap class="w-7 h-7" />
      </div>
      <h1 class="text-2xl font-black tracking-tight text-white">
        {store.config?.server?.title || 'Janus Lab'}
      </h1>
      <p class="text-xs text-slate-400 max-w-xs">
        {store.config?.server?.subtitle || 'Hybrid Gaming & On-Demand Homelab'}
      </p>
    </div>

    {@render pinCard()}

    <div class="mt-6 flex items-center gap-2 text-xs text-slate-500">
      <ShieldAlert class="w-4 h-4 text-slate-500" />
      <span>Protected by hardware-isolated rate limiting</span>
    </div>
  </div>
{:else if !mandatory && store.activeModal === 'pin'}
  <div
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
    role="dialog"
    aria-modal="true"
    aria-labelledby="pin-modal-title"
  >
    {@render pinCard()}
  </div>
{/if}
