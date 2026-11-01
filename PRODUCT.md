# Product: JanusDeck

## Purpose & Positioning
JanusDeck is the command deck and mobile dashboard for hybrid gaming and dual-boot homelabs. It bridges the gap between 24/7 Linux server workloads (Docker, Coolify, WireGuard, storage) and on-demand Windows 11 gaming, providing physical host power controls, one-shot OS switching via GRUB (`grub-reboot`), real-time hardware telemetry (CPU, RAM, NVIDIA GPU, Storage), and a unified homelab service directory.

## Primary Users & Scenarios
- **Homelab Operators & PC Gamers**: Users running powerful dual-purpose hardware (e.g. Intel Core i7-8700K, 40GB DDR4, NVIDIA RTX 2070, mixed SSD/HDD storage).
- **Remote / Mobile Control**: Accessing the server dashboard from a phone or tablet (via LAN or WireGuard VPN) to check system thermals, launch homelab services, or trigger a reboot into Windows for gaming without physically interacting with the machine or boot menus.
- **Fail-Safe Operation**: Operators requiring guaranteed automatic fallback to Linux Server upon next reboot, preventing remote lockouts.

## Core Workflows
1. **Live Telemetry & Diagnostics**: Inspect real-time CPU load/frequency/temp, RAM & Swap utilization, GPU VRAM/temperature/load, and storage pools via SSE.
2. **One-Shot OS Switching**: Select Windows 11 (or alternative OS target), enter PIN, review 5-second cancellation window, and reboot. On subsequent reboot from Windows, GRUB naturally returns to Linux Server.
3. **Protected Host Power Actions**: Reboot Ubuntu Server or trigger ACPI graceful shutdown via systemd D-Bus, guarded by master PIN authentication and countdown abort.
4. **Service Directory & Dynamic Management**: Manage homelab bookmarks (Coolify, WireGuard, Docmost, Uptime Kuma, Vaultwarden, etc.) with automated HTTP health check indicators (online/offline latency). Dynamically register, edit, and organize services with persistent PostgreSQL 18 database storage and master PIN protection.

## Platform & Stack
- **Platform**: Web (mobile-responsive and desktop dashboard).
- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0 (async), asyncpg, `psutil`, `pynvml`, systemd D-Bus, `grub-editenv`.
- **Database**: PostgreSQL 18 (multi-tenant shared homelab database on `coolify` network).
- **Frontend**: Svelte 5 (Runes) + Tailwind CSS design system + Lucide icons, SSE event streaming. Precompiled production assets served directly by FastAPI.
- **Security**: Master PIN authentication, session token caching, constant-time verification, brute-force rate-limiting lockout.

## Constraints & Invariants
- Destructive power actions must require PIN verification and provide an immediate 5-second cancellation abort mechanism.
- Must operate reliably in local-network or VPN environments without requiring continuous public internet connectivity.
- Telemetry must degrade gracefully when NVML (GPU) or thermal sensors are unavailable.
