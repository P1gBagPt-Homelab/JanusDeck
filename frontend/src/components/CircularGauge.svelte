<script lang="ts">
  interface Props {
    value: number;
    color?: 'cyan' | 'indigo' | 'emerald' | 'amber' | 'rose';
    size?: number;
    strokeWidth?: number;
    unit?: string;
  }

  let {
    value = 0,
    color = 'cyan',
    size = 120,
    strokeWidth = 8,
    unit = '% LOAD'
  }: Props = $props();

  const radius = $derived((size - strokeWidth * 2) / 2);
  const circumference = $derived(2 * Math.PI * radius);
  const clampedValue = $derived(Math.max(0, Math.min(100, Math.round(value))));
  const strokeDashoffset = $derived(circumference - (clampedValue / 100) * circumference);

  const colorMap = {
    cyan: '#38bdf8',
    indigo: '#6366f1',
    emerald: '#34d399',
    amber: '#fbbf24',
    rose: '#f43f5e',
  };
</script>

<div class="relative flex items-center justify-center mx-auto" style="width: {size}px; height: {size}px;">
  <svg class="-rotate-90 w-full h-full" viewBox="0 0 {size} {size}" aria-hidden="true">
    <circle
      cx={size / 2}
      cy={size / 2}
      r={radius}
      class="fill-none stroke-white/[0.08]"
      stroke-width={strokeWidth}
    />
    <circle
      cx={size / 2}
      cy={size / 2}
      r={radius}
      class="fill-none transition-[stroke-dashoffset] duration-700 ease-out"
      stroke={colorMap[color]}
      stroke-width={strokeWidth}
      stroke-linecap="round"
      stroke-dasharray={circumference}
      style="stroke-dashoffset: {strokeDashoffset}px;"
    />
  </svg>
  <div class="absolute inset-0 flex flex-col items-center justify-center text-center select-none pointer-events-none">
    <span class="text-2xl font-bold tabular-nums text-slate-100 leading-none">
      {clampedValue}
    </span>
    {#if unit}
      <span class="text-[10px] font-semibold text-slate-400 mt-1 tracking-wider uppercase">
        {unit}
      </span>
    {/if}
  </div>
</div>
