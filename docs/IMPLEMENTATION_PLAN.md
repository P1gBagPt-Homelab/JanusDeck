# JanusDeck: Complete Execution & Implementation Plan

This roadmap provides the exact step-by-step implementation plan for building and deploying **JanusDeck**. It is structured into actionable phases that can be executed sequentially when development begins.

---

## 🗺️ Execution Phases Overview

| Phase | Milestone | Scope / Deliverables | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Backend Engine & Hardware API** | FastAPI setup, `psutil` system metrics, NVIDIA NVML/`pynvml` telemetry, SSE streaming endpoint. | ✅ Complete |
| **Phase 2** | **Host Power & Dual-Boot Bridge** | systemd DBus interface (poweroff/reboot), `/boot/grubenv` editor (`grub-reboot` execution), PIN authentication gate. | ✅ Complete |
| **Phase 3** | **Frontend UI & Mobile Dashboard** | Dark-mode glassmorphic interface (Tailwind + Lucide), live gauge updates, service bookmark grid, PIN modal. | ✅ Complete |
| **Phase 4** | **Containerization & Multi-Arch Build** | Optimized `Dockerfile`, permission hardening, NVIDIA container runtime testing. | ✅ Complete |
| **Phase 5** | **Coolify Deployment & Traefik Routing** | Coolify Docker Compose deployment, volume mounts (`dbus`, `/boot`), SSL via Let's Encrypt at `control.janus-lab.duckdns.org`. | ⏳ Pending |
| **Phase 6** | **Failsafe & Dual-Boot Verification** | Real-world reboot tests, one-shot Windows boot verification, auto-revert to Linux validation. | ⏳ Pending |

---

## Detailed Step-by-Step Breakdown

### Phase 1: Backend Engine & Telemetry Pipeline (`src/`)

1. **Project Dependencies (`requirements.txt`)**:
   * `fastapi`: Async REST API & Server-Sent Events.
   * `uvicorn[standard]`: ASGI production server.
   * `psutil`: Native CPU, RAM, Disk, and system process inspection.
   * `pynvml`: Direct NVIDIA driver bindings for live RTX 2070 load, VRAM, and temperatures.
   * `pyyaml`: Configuration file parser for `config.yaml`.

2. **Core Modules to Build**:
   * `src/config.py`: Loads and validates `config.yaml` with fallback environment variables.
   * `src/telemetry.py`: Asynchronously gathers CPU load, RAM utilization, storage pool percentages, and GPU metrics without blocking the event loop.
   * `src/main.py`:
     * Serves frontend static assets.
     * `GET /api/stats`: SSE endpoint broadcasting real-time metrics every 2 seconds.
     * `GET /api/services`: Evaluates HTTP health check pings for registered homelab services.

---

### Phase 2: Host Power & Dual-Boot Bridge (`src/power.py`) - ✅ Completed

1. **System Power Actions via DBus**:
   * Interfaced with `/var/run/dbus/system_bus_socket` (`src/power.py`).
   * Standard D-Bus method calls to `org.freedesktop.login1.Manager`:
     * `PowerOff(interactive=True)`
     * `Reboot(interactive=True)`
   * Multi-tier fallback strategy: `dbus-send` -> `busctl` -> `systemctl` -> graceful simulation mode.

2. **Dual-Boot Switching via GRUB**:
   * Discovers and parses boot entries from `/boot/grub/grub.cfg` (`src/grub.py`).
   * Schedules one-shot boot entry via `grub-editenv /boot/grub/grubenv set next_entry="..."` with pure Python 1024-byte block format fallback.
   * Trigger reboot execution and clear next_entry actions.

3. **Security Gate**:
   * Constant-time PIN verification using `secrets.compare_digest` against `config.yaml` or `JANUS_PIN` (`src/security.py`).
   * Rate limiting and lockout protection against brute-force attacks (HTTP 429 lockout response).
   * Fully exposed via FastAPI endpoints:
     * `POST /api/auth/verify` & `GET /api/auth/status`
     * `GET /api/power/status` & `GET /api/power/targets`
     * `POST /api/power/reboot`, `POST /api/power/shutdown`, `POST /api/power/switch-os`, `POST /api/power/clear-next-entry`

---

### Phase 3: Frontend Interface (`web/`) — Powered by Impeccable - ✅ Completed

1. **Design System & Craft Workflow (Impeccable)**:
   * Built and refined using **Impeccable** (`4.8.0`) standards and playbooks (`shape`, `craft-floor`, `audit`, `polish`).
   * Mode: **Operate / Dashboard** with high-density scanability, purposeful micro-interactions, and pristine responsive ergonomics.
   * Aesthetic: Project Janus slate dark background (`#0b0f19`), neon cyan/violet accents, glassmorphic card depth with subtle borders, fluid typography, and dark-theme high-contrast gauges.
2. **Interactive Components**:
   * **Telemetry Bar**: High-refresh circular / horizontal gauge bars for CPU (i7-8700K), RAM (40GB), GPU (RTX 2070), and Disks (LVM + HDD) via SSE.
   * **Service Launcher Grid**: Quick links with real-time green/red availability badges and resilient fallback states.
   * **Power Control Deck**:
     * 🟢 *Reboot Ubuntu Server*
     * 🛑 *Graceful Shutdown*
     * 🎮 *Switch to Windows Gaming Mode*
   * **PIN Security Modal**: Accessible keypad input with 5-second countdown timer allowing user cancellation before execution.
3. **Quality & Polish Verification**:
   * Pre-edit craft floor checklist adherence (`reference/craft-floor.md`).
   * Technical checks (`audit`: a11y, mobile responsive layout, touch target sizing, keyboard navigation).

---

### Phase 4: Docker Containerization (`Dockerfile`) - ✅ Completed

1. **Base Image**: `python:3.12-slim-bookworm` for minimal footprint (<150 MB).
2. **Host Bridge Utilities**: Install `grub-common` and `dbus` inside the container so GRUB utilities function natively.
3. **Non-Root Execution Safeguards**: Ensure appropriate DBus socket group permissions.

---

### Phase 5: Coolify Deployment on Project Janus

1. **Coolify Service Configuration**:
   * Deploy via **Docker Compose** in Coolify dashboard.
   * Set domain: `https://control.janus-lab.duckdns.org`.
   * Map volumes:
     ```yaml
     volumes:
       - /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket:ro
       - /boot:/boot:rw
       - ./config.yaml:/app/config.yaml:ro
     ```
   * Enable NVIDIA GPU reservation for RTX 2070 pass-through.
2. **Reverse Proxy & SSL**:
   * Traefik automatically routes incoming HTTPS traffic and provisions Let's Encrypt certificates.

---

### Phase 6: Verification & Dual-Boot Testing

1. **Telemetry Verification**:
   * Confirm live RTX 2070 VRAM and temperatures match `nvidia-smi` on the host.
2. **Safe Reboot Test**:
   * Tap "Reboot Server" in web UI; enter PIN.
   * Verify machine reboots and returns automatically to Linux Server.
3. **Gaming Mode Switch Test**:
   * Tap "Switch to Windows"; enter PIN.
   * Verify GRUB boots into Windows 11 without manual key presses.
   * Shut down Windows; verify subsequent startup boots back into Ubuntu Server.
