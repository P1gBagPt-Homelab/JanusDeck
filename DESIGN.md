# Design System: JanusDeck

## Mode & Aesthetic
- **Mode**: **Operate / Dashboard**
  - High-density scanability, instant legibility, ergonomic thumb-reach on mobile, zero visual clutter.
  - Controls name their actions clearly; errors name the root cause and recovery pathway.
- **Aesthetic**: **Project Janus Slate & Cyberpunk Precision**
  - Deep slate ground (`#0b0f19`) with elevated card depths (`#111827`, `#151e32`).
  - Subtle micro-borders (`rgba(255, 255, 255, 0.08)`) with soft contextual hover glows (`rgba(56, 189, 248, 0.25)`).
  - High-contrast telemetry gauges with tabular figures for jitter-free live metric reading.

## Color Tokens
```css
:root {
  /* Ground & Surfaces */
  --bg-ground: #0b0f19;
  --bg-surface: #111827;
  --bg-surface-elevated: #162036;
  --bg-surface-hover: #1e2942;
  --bg-card: rgba(17, 24, 39, 0.75);

  /* Borders & Dividers */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-medium: rgba(255, 255, 255, 0.16);
  --border-focus: #38bdf8;

  /* Typography & Foreground */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;

  /* Accent & Telemetry Hues */
  --accent-cyan: #38bdf8;
  --accent-violet: #a855f7;
  --accent-emerald: #34d399;
  --accent-amber: #fbbf24;
  --accent-rose: #f43f5e;

  /* Functional States */
  --status-online: #34d399;
  --status-offline: #f43f5e;
  --status-pending: #fbbf24;
}
```

## Typography & Numbers
- **Font Stack**: System UI sans-serif (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif`).
- **Telemetry & Data**: Monospace tabular numerals (`font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-variant-numeric: tabular-nums;`).
- **Scale**:
  - Headings: bold, tight tracking (-0.02em to -0.04em).
  - Gauge values: 24px-28px tabular font.
  - Labels & subtitles: 12px-13px uppercase tracking-wider or standard sentence case.

## Component Specifications
1. **Header & Status Rail**:
   - Machine hostname, kernel/OS name, formatted uptime, live SSE connection heartbeat pill with pulsating green/amber indicator.
   - PIN unlock status indicator with quick lock/unlock trigger.
2. **Telemetry Gauge Cluster**:
   - CPU: Arc gauge + core load %, frequency (GHz), package temperature (°C) with color transitions (<65°C Cyan, 65-80°C Amber, >80°C Rose).
   - RAM: Arc gauge + used/total GB, swap breakdown.
   - GPU: Arc gauge + load %, VRAM used/total GB, temperature (°C), fan speed %, power (W).
   - Storage Pools: Segmented linear progress bars for each mounted partition (Root SSD / Cold HDD) with percentage and free space.
3. **Power Deck**:
   - Three differentiated primary action cards:
     - 🟢 Reboot Server (`login1 Reboot`)
     - 🛑 Graceful Shutdown (`login1 PowerOff`)
     - 🎮 Switch to Windows (`grub-reboot` + reboot)
   - Active one-shot boot banner when `next_entry` is staged, with one-click "Cancel / Revert to Linux" action.
4. **PIN Security Modal**:
   - Modal backdrop with high blur (`backdrop-blur-md`).
   - Clean numeric keypad for mobile touch + auto-focused masked digit input.
   - Destructive action confirmation: 5-second countdown timer bar with prominent "Abort / Cancel" button before the execution request is sent.
5. **Service Directory Grid**:
   - Categorized cards with quick launch button, health status pill (200 OK latency in ms or Offline badge), and external link fallback.
   - Filter / search or grouped by category.
