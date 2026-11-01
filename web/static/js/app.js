/**
 * JanusDeck Frontend Application Logic
 * Telemetry SSE Engine, Dual-Boot Switcher & PIN-Guarded Power Deck
 */
(function() {
  'use strict';

  // Constants & State
  const GAUGE_RADIUS = 48;
  const GAUGE_CIRCUMFERENCE = 2 * Math.PI * GAUGE_RADIUS; // ~301.59

  const state = {
    config: null,
    sessionToken: sessionStorage.getItem('janus_session_token') || null,
    sessionExpiresAt: null,
    pinBuffer: '',
    pendingAction: null, // { type: 'reboot'|'shutdown'|'switch-os', targetId?: string, label: string }
    countdownTimer: null,
    countdownRemaining: 5,
    lockoutTimer: null,
    sseSource: null,
    reconnectAttempts: 0,
    servicesData: null,
    powerStatus: null
  };

  // DOM Elements Cache
  const elements = {
    // Header
    statusPill: document.getElementById('connection-status'),
    hostPill: document.getElementById('host-info'),
    uptimeDisplay: document.getElementById('uptime-display'),
    lockBtn: document.getElementById('btn-lock-toggle'),
    stagedBanner: document.getElementById('staged-banner'),
    stagedTargetName: document.getElementById('staged-target-name'),
    btnClearNext: document.getElementById('btn-clear-next'),

    // Telemetry Gauges
    cpuGauge: document.getElementById('cpu-gauge-progress'),
    cpuVal: document.getElementById('cpu-val'),
    cpuFreq: document.getElementById('cpu-freq'),
    cpuTempBadge: document.getElementById('cpu-temp-badge'),
    cpuCoreGrid: document.getElementById('cpu-core-grid'),

    ramGauge: document.getElementById('ram-gauge-progress'),
    ramVal: document.getElementById('ram-val'),
    ramUsed: document.getElementById('ram-used'),
    ramSwap: document.getElementById('ram-swap'),

    gpuGauge: document.getElementById('gpu-gauge-progress'),
    gpuVal: document.getElementById('gpu-val'),
    gpuName: document.getElementById('gpu-name'),
    gpuVram: document.getElementById('gpu-vram'),
    gpuTempBadge: document.getElementById('gpu-temp-badge'),
    gpuPower: document.getElementById('gpu-power'),

    storageContainer: document.getElementById('storage-pools-container'),

    // Power Actions
    btnSwitchWindows: document.getElementById('btn-switch-windows'),
    btnRebootServer: document.getElementById('btn-reboot-server'),
    btnShutdownServer: document.getElementById('btn-shutdown-server'),

    // Services
    servicesContainer: document.getElementById('services-container'),
    btnRefreshServices: document.getElementById('btn-refresh-services'),

    // Modal & PIN
    modalOverlay: document.getElementById('security-modal'),
    modalTitle: document.getElementById('modal-title'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    pinKeypadView: document.getElementById('pin-keypad-view'),
    pinDots: document.querySelectorAll('.pin-dot'),
    lockoutMsg: document.getElementById('lockout-msg'),
    lockoutCountdown: document.getElementById('lockout-countdown'),

    // 5-Second Countdown View
    countdownView: document.getElementById('countdown-view'),
    countdownNum: document.getElementById('countdown-num'),
    countdownCircle: document.getElementById('countdown-progress-circle'),
    countdownTarget: document.getElementById('countdown-target-label'),
    btnAbortCountdown: document.getElementById('btn-abort-action'),

    // Toast Container
    toastContainer: document.getElementById('toast-container')
  };

  // Helper: Toast Notifications
  function showToast(message, type = 'info', duration = 3500) {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let iconName = 'info';
    if (type === 'success') iconName = 'check';
    if (type === 'error') iconName = 'alert-triangle';

    toast.innerHTML = `
      <span class="toast-icon">${window.JanusIcons ? window.JanusIcons.get(iconName, 'w-5 h-5') : ''}</span>
      <span class="toast-message">${escapeHtml(message)}</span>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }

  // Helper: Formatting bytes
  function formatBytes(bytes, decimals = 1) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  // Helper: Format Uptime
  function formatUptime(seconds) {
    if (!seconds || seconds <= 0) return 'Just started';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);

    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0 || days > 0) parts.push(`${hours}h`);
    parts.push(`${mins}m`);
    return parts.join(' ');
  }

  // Update SVG Circular Gauge
  function updateCircularGauge(circleEl, percent, thresholdClass = 'cyan') {
    if (!circleEl) return;
    const clamped = Math.max(0, Math.min(100, percent || 0));
    const offset = GAUGE_CIRCUMFERENCE - (clamped / 100) * GAUGE_CIRCUMFERENCE;
    circleEl.style.strokeDashoffset = offset;

    // Reset color classes
    circleEl.classList.remove('cyan', 'violet', 'emerald', 'amber', 'rose');
    circleEl.classList.add(thresholdClass);
  }

  // ============================================================================
  // Telemetry SSE Stream & Snapshot Fallback
  // ============================================================================

  function setConnectionStatus(statusClass, label) {
    if (!elements.statusPill) return;
    elements.statusPill.className = `status-pill ${statusClass}`;
    elements.statusPill.innerHTML = `
      <span class="pulse-dot"></span>
      <span class="status-label">${label}</span>
    `;
  }

  function initTelemetryStream() {
    if (state.sseSource) {
      state.sseSource.close();
    }

    setConnectionStatus('connecting', 'Connecting...');

    try {
      state.sseSource = new EventSource('/api/stats');

      state.sseSource.onopen = function() {
        state.reconnectAttempts = 0;
        setConnectionStatus('online', 'Live');
      };

      state.sseSource.onmessage = function(event) {
        try {
          const metrics = JSON.parse(event.data);
          renderTelemetry(metrics);
        } catch (err) {
          console.error('Error parsing SSE telemetry frame:', err);
        }
      };

      state.sseSource.onerror = function() {
        state.sseSource.close();
        state.sseSource = null;
        state.reconnectAttempts++;

        setConnectionStatus('offline', 'Reconnecting...');

        // Fallback: poll snapshot immediately once
        fetchSnapshot();

        // Exponential backoff reconnect
        const delay = Math.min(10000, 1500 * Math.pow(1.5, state.reconnectAttempts));
        setTimeout(initTelemetryStream, delay);
      };
    } catch (e) {
      console.warn('SSE not supported or failed, falling back to snapshot polling');
      fetchSnapshot();
      setInterval(fetchSnapshot, 3000);
    }
  }

  async function fetchSnapshot() {
    try {
      const res = await fetch('/api/stats/snapshot');
      if (res.ok) {
        const metrics = await res.json();
        renderTelemetry(metrics);
      }
    } catch (e) {
      console.warn('Snapshot fetch failed:', e);
    }
  }

  // Render Telemetry Data into DOM
  function renderTelemetry(metrics) {
    if (!metrics) return;

    // 1. Host Uptime & System info
    if (metrics.host || metrics.system) {
      const sys = metrics.host || metrics.system;
      if (sys.uptime_seconds && elements.uptimeDisplay) {
        elements.uptimeDisplay.textContent = formatUptime(sys.uptime_seconds);
      }
      if (sys.hostname && elements.hostPill) {
        elements.hostPill.innerHTML = `
          ${window.JanusIcons ? window.JanusIcons.get('server', 'w-3.5 h-3.5') : ''}
          <span>${escapeHtml(sys.hostname)} (${escapeHtml(sys.platform || 'Linux')})</span>
        `;
      }
    }

    // 2. CPU
    if (metrics.cpu) {
      const cpu = metrics.cpu;
      const load = Math.round(cpu.overall_percent || 0);
      if (elements.cpuVal) elements.cpuVal.textContent = load;

      let cpuClass = 'cyan';
      if (load > 85) cpuClass = 'rose';
      else if (load > 65) cpuClass = 'amber';
      updateCircularGauge(elements.cpuGauge, load, cpuClass);

      if (elements.cpuFreq && cpu.frequency_current) {
        const ghz = (cpu.frequency_current / 1000).toFixed(2);
        elements.cpuFreq.textContent = `${ghz} GHz`;
      }

      if (elements.cpuTempBadge) {
        if (cpu.temperature_celsius != null) {
          const temp = Math.round(cpu.temperature_celsius);
          let tempClass = 'normal';
          if (temp >= 80) tempClass = 'hot';
          else if (temp >= 65) tempClass = 'warm';

          elements.cpuTempBadge.className = `temp-badge ${tempClass}`;
          elements.cpuTempBadge.innerHTML = `
            ${window.JanusIcons ? window.JanusIcons.get('thermometer', 'w-3 h-3') : ''}
            <span>${temp}°C</span>
          `;
          elements.cpuTempBadge.style.display = 'inline-flex';
        } else {
          elements.cpuTempBadge.style.display = 'none';
        }
      }

      // Per-core visualizer
      if (elements.cpuCoreGrid && cpu.per_cpu && Array.isArray(cpu.per_cpu)) {
        elements.cpuCoreGrid.innerHTML = cpu.per_cpu.slice(0, 12).map((val) => {
          const pct = Math.max(0, Math.min(100, Math.round(val)));
          let color = 'var(--accent-cyan)';
          if (pct > 80) color = 'var(--accent-rose)';
          else if (pct > 60) color = 'var(--accent-amber)';
          return `<div class="core-bar-cell" title="Core: ${pct}%"><div class="core-bar-fill" style="height:${pct}%;background:${color};"></div></div>`;
        }).join('');
      }
    }

    // 3. RAM
    if (metrics.memory) {
      const mem = metrics.memory;
      const load = Math.round(mem.percent || 0);
      if (elements.ramVal) elements.ramVal.textContent = load;

      let memClass = 'violet';
      if (load > 90) memClass = 'rose';
      else if (load > 75) memClass = 'amber';
      updateCircularGauge(elements.ramGauge, load, memClass);

      if (elements.ramUsed) {
        const usedGb = (mem.used_bytes / (1024 ** 3)).toFixed(1);
        const totalGb = Math.round(mem.total_bytes / (1024 ** 3));
        elements.ramUsed.textContent = `${usedGb} / ${totalGb} GB`;
      }

      if (elements.ramSwap) {
        elements.ramSwap.textContent = `${Math.round(mem.swap_percent || 0)}%`;
      }
    }

    // 4. GPU
    if (metrics.gpu) {
      const gpu = metrics.gpu;
      if (gpu.available) {
        const load = Math.round(gpu.load_percent || 0);
        if (elements.gpuVal) elements.gpuVal.textContent = load;

        let gpuClass = 'emerald';
        if (load > 85) gpuClass = 'rose';
        else if (load > 60) gpuClass = 'amber';
        updateCircularGauge(elements.gpuGauge, load, gpuClass);

        if (elements.gpuName && gpu.name) {
          elements.gpuName.textContent = gpu.name.replace('NVIDIA GeForce ', '');
        }

        if (elements.gpuVram) {
          const usedGb = (gpu.memory_used_bytes / (1024 ** 3)).toFixed(1);
          const totalGb = Math.round(gpu.memory_total_bytes / (1024 ** 3));
          elements.gpuVram.textContent = `${usedGb} / ${totalGb} GB`;
        }

        if (elements.gpuTempBadge) {
          if (gpu.temperature_celsius != null) {
            const temp = Math.round(gpu.temperature_celsius);
            let tempClass = 'normal';
            if (temp >= 82) tempClass = 'hot';
            else if (temp >= 70) tempClass = 'warm';

            elements.gpuTempBadge.className = `temp-badge ${tempClass}`;
            elements.gpuTempBadge.innerHTML = `
              ${window.JanusIcons ? window.JanusIcons.get('thermometer', 'w-3 h-3') : ''}
              <span>${temp}°C</span>
            `;
            elements.gpuTempBadge.style.display = 'inline-flex';
          }
        }

        if (elements.gpuPower) {
          if (gpu.power_usage_w != null) {
            elements.gpuPower.textContent = `${Math.round(gpu.power_usage_w)}W`;
          } else {
            elements.gpuPower.textContent = '--';
          }
        }
      } else {
        // GPU unavailable or idle server mode
        if (elements.gpuVal) elements.gpuVal.textContent = '0';
        updateCircularGauge(elements.gpuGauge, 0, 'emerald');
        if (elements.gpuName) elements.gpuName.textContent = 'GPU Idle / Headless';
        if (elements.gpuVram) elements.gpuVram.textContent = 'Offline';
        if (elements.gpuTempBadge) elements.gpuTempBadge.style.display = 'none';
        if (elements.gpuPower) elements.gpuPower.textContent = '--';
      }
    }

    // 5. Storage Pools
    if (metrics.storage && Array.isArray(metrics.storage) && elements.storageContainer) {
      elements.storageContainer.innerHTML = metrics.storage.map(pool => {
        const pct = Math.round(pool.percent || 0);
        const usedStr = formatBytes(pool.used_bytes);
        const totalStr = formatBytes(pool.total_bytes);
        const freeStr = formatBytes(pool.free_bytes);
        const isWarn = pct > 85;

        return `
          <div class="linear-progress-wrapper">
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.75rem;">
              <span style="font-weight:600; color:var(--text-primary); display:flex; align-items:center; gap:0.35rem;">
                ${window.JanusIcons ? window.JanusIcons.get('hard-drive', 'w-3.5 h-3.5 text-cyan-400') : ''}
                ${escapeHtml(pool.name || pool.path)}
              </span>
              <span class="tabular-nums" style="color:var(--text-secondary);">${pct}% (${freeStr} free)</span>
            </div>
            <div class="linear-progress-track">
              <div class="linear-progress-fill ${isWarn ? 'warning' : ''}" style="width: ${pct}%;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.6875rem; color:var(--text-muted);" class="tabular-nums">
              <span>Used: ${usedStr}</span>
              <span>Total: ${totalStr}</span>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // ============================================================================
  // Services Health Evaluation & Rendering
  // ============================================================================

  async function fetchServices(isManualRefresh = false) {
    if (isManualRefresh && elements.btnRefreshServices) {
      elements.btnRefreshServices.classList.add('animate-spin');
    }

    try {
      const res = await fetch('/api/services');
      if (res.ok) {
        const data = await res.json();
        state.servicesData = data.services || [];
        renderServices(state.servicesData);
        if (isManualRefresh) {
          showToast('Service availability updated', 'success', 2500);
        }
      }
    } catch (err) {
      console.error('Failed to fetch services:', err);
      if (isManualRefresh) {
        showToast('Failed to check service health', 'error');
      }
    } finally {
      if (elements.btnRefreshServices) {
        elements.btnRefreshServices.classList.remove('animate-spin');
      }
    }
  }

  function renderServices(services) {
    if (!elements.servicesContainer) return;
    if (!services || services.length === 0) {
      elements.servicesContainer.innerHTML = `
        <div style="text-align:center; padding:2rem; color:var(--text-muted); font-size:0.875rem;">
          No homelab services configured. Add items to <code>config.yaml</code>.
        </div>
      `;
      return;
    }

    // Group services by category
    const categories = {};
    services.forEach(svc => {
      const cat = svc.category || 'General Services';
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(svc);
    });

    let html = '';
    for (const [catName, items] of Object.entries(categories)) {
      html += `
        <div class="service-category-group">
          <div class="category-title">
            ${escapeHtml(catName)}
          </div>
          <div class="service-grid">
            ${items.map(svc => renderServiceCard(svc)).join('')}
          </div>
        </div>
      `;
    }

    elements.servicesContainer.innerHTML = html;

    // Attach click listeners for copy buttons and links
    elements.servicesContainer.querySelectorAll('.btn-copy-url').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const url = btn.getAttribute('data-url');
        if (url) {
          navigator.clipboard.writeText(url).then(() => {
            showToast('Service URL copied to clipboard', 'info', 2000);
          });
        }
      });
    });
  }

  function renderServiceCard(svc) {
    const isOnline = svc.online === true;
    const latency = svc.response_time_ms ? `${Math.round(svc.response_time_ms)}ms` : null;
    const iconName = svc.icon || 'server';
    const launchUrl = svc.url || svc.external_url || '#';

    return `
      <div class="service-card" onclick="window.open('${escapeHtml(launchUrl)}', '_blank', 'noopener')">
        <div class="service-card-main">
          <div class="service-icon-box">
            ${window.JanusIcons ? window.JanusIcons.get(iconName, 'w-5 h-5') : ''}
          </div>
          <div class="service-info">
            <div class="service-info-header">
              <span class="service-name">${escapeHtml(svc.name)}</span>
              <span class="health-badge ${isOnline ? 'up' : 'down'}">
                <span class="pulse-dot" style="width:6px; height:6px;"></span>
                <span>${isOnline ? (latency || 'Online') : 'Offline'}</span>
              </span>
            </div>
            <span class="service-desc">${escapeHtml(svc.description || svc.url)}</span>
          </div>
        </div>
        <div class="service-actions" onclick="event.stopPropagation();">
          <button class="btn btn-secondary btn-icon-only btn-copy-url" data-url="${escapeHtml(launchUrl)}" title="Copy Link" aria-label="Copy URL">
            ${window.JanusIcons ? window.JanusIcons.get('copy', 'w-4 h-4') : ''}
          </button>
          <a href="${escapeHtml(launchUrl)}" target="_blank" rel="noopener" class="btn btn-secondary btn-icon-only" title="Launch" aria-label="Open Service">
            ${window.JanusIcons ? window.JanusIcons.get('external-link', 'w-4 h-4') : ''}
          </a>
        </div>
      </div>
    `;
  }

  // ============================================================================
  // Host Power & GRUB Staged Boot Status
  // ============================================================================

  async function checkPowerStatus() {
    try {
      const res = await fetch('/api/power/status');
      if (res.ok) {
        state.powerStatus = await res.json();
        updatePowerUI(state.powerStatus);
      }
    } catch (e) {
      console.warn('Failed to fetch power status:', e);
    }
  }

  function updatePowerUI(status) {
    if (!status) return;

    // Check if next_entry is set
    if (status.next_entry && elements.stagedBanner && elements.stagedTargetName) {
      elements.stagedTargetName.textContent = status.next_entry;
      elements.stagedBanner.classList.add('active');
    } else if (elements.stagedBanner) {
      elements.stagedBanner.classList.remove('active');
    }
  }

  // ============================================================================
  // PIN Security Modal & 5-Second Cancellation Gate
  // ============================================================================

  function openPinModal(action) {
    state.pendingAction = action;
    state.pinBuffer = '';
    updatePinDots();

    // Check if user is already authenticated with valid session
    if (state.sessionToken) {
      proceedToCountdown();
      return;
    }

    if (elements.modalTitle) {
      elements.modalTitle.innerHTML = `
        ${window.JanusIcons ? window.JanusIcons.get('lock', 'w-5 h-5 text-cyan-400') : ''}
        <span>Security Verification</span>
      `;
    }

    // Show Keypad, Hide Countdown
    if (elements.pinKeypadView) elements.pinKeypadView.style.display = 'block';
    if (elements.countdownView) elements.countdownView.classList.remove('active');
    if (elements.lockoutMsg) elements.lockoutMsg.classList.remove('active');

    if (elements.modalOverlay) {
      elements.modalOverlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeModal() {
    if (state.countdownTimer) {
      clearInterval(state.countdownTimer);
      state.countdownTimer = null;
    }
    state.pendingAction = null;
    state.pinBuffer = '';

    if (elements.modalOverlay) {
      elements.modalOverlay.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  function updatePinDots() {
    elements.pinDots.forEach((dot, idx) => {
      if (idx < state.pinBuffer.length) {
        dot.classList.add('filled');
      } else {
        dot.classList.remove('filled');
      }
    });
  }

  function handleKeypadInput(digit) {
    if (state.pinBuffer.length >= 6) return;
    state.pinBuffer += digit;
    updatePinDots();

    // Auto verify once 4 to 6 digits reached (standard length)
    if (state.pinBuffer.length >= 4) {
      verifyPinAttempt();
    }
  }

  function handleKeypadBackspace() {
    if (state.pinBuffer.length > 0) {
      state.pinBuffer = state.pinBuffer.slice(0, -1);
      updatePinDots();
    }
  }

  function handleKeypadClear() {
    state.pinBuffer = '';
    updatePinDots();
  }

  async function verifyPinAttempt() {
    const pin = state.pinBuffer;
    try {
      const res = await fetch('/api/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin: pin })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.session_token) {
          state.sessionToken = data.session_token;
          sessionStorage.setItem('janus_session_token', data.session_token);
          updateLockState(true);
        }
        proceedToCountdown();
      } else if (res.status === 429) {
        // Locked out
        const err = await res.json();
        startLockoutCountdown(err.lockout_remaining_seconds || 60);
      } else {
        // Invalid PIN
        shakePinDots();
        state.pinBuffer = '';
        updatePinDots();
        showToast('Invalid PIN entered', 'error', 2500);
      }
    } catch (e) {
      console.error('PIN verify request error:', e);
      showToast('Connection error during PIN verification', 'error');
    }
  }

  function shakePinDots() {
    const wrap = document.querySelector('.pin-dots');
    if (!wrap) return;
    wrap.style.animation = 'shake 0.3s ease';
    setTimeout(() => wrap.style.animation = '', 350);
  }

  function startLockoutCountdown(seconds) {
    if (elements.lockoutMsg && elements.lockoutCountdown) {
      elements.lockoutMsg.classList.add('active');
      let remaining = seconds;
      elements.lockoutCountdown.textContent = remaining;

      if (state.lockoutTimer) clearInterval(state.lockoutTimer);
      state.lockoutTimer = setInterval(() => {
        remaining--;
        elements.lockoutCountdown.textContent = remaining;
        if (remaining <= 0) {
          clearInterval(state.lockoutTimer);
          elements.lockoutMsg.classList.remove('active');
        }
      }, 1000);
    }
  }

  // ============================================================================
  // 5-Second Cancellation Gate View
  // ============================================================================

  function proceedToCountdown() {
    if (!state.pendingAction) return;

    if (elements.pinKeypadView) elements.pinKeypadView.style.display = 'none';
    if (elements.modalOverlay) {
      elements.modalOverlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    if (elements.modalTitle) {
      elements.modalTitle.innerHTML = `
        ${window.JanusIcons ? window.JanusIcons.get('alert-triangle', 'w-5 h-5 text-rose-500') : ''}
        <span>Confirm Execution</span>
      `;
    }

    if (elements.countdownView) {
      elements.countdownView.classList.add('active');
    }

    if (elements.countdownTarget) {
      elements.countdownTarget.textContent = state.pendingAction.label;
    }

    state.countdownRemaining = 5;
    if (elements.countdownNum) elements.countdownNum.textContent = '5';

    const circleCircumference = 2 * Math.PI * 46; // r=46
    if (elements.countdownCircle) {
      elements.countdownCircle.style.strokeDashoffset = '0';
    }

    if (state.countdownTimer) clearInterval(state.countdownTimer);

    state.countdownTimer = setInterval(() => {
      state.countdownRemaining--;
      if (elements.countdownNum) {
        elements.countdownNum.textContent = Math.max(0, state.countdownRemaining);
      }

      if (elements.countdownCircle) {
        const offset = circleCircumference * (1 - (state.countdownRemaining / 5));
        elements.countdownCircle.style.strokeDashoffset = offset;
      }

      if (state.countdownRemaining <= 0) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
        executePendingPowerAction();
      }
    }, 1000);
  }

  async function executePendingPowerAction() {
    const action = state.pendingAction;
    if (!action) return;

    if (elements.countdownView) {
      elements.countdownView.innerHTML = `
        <div style="padding: 2rem 0; text-align: center;">
          <div class="pulse-dot" style="width: 16px; height: 16px; margin: 0 auto 1rem;"></div>
          <h3 style="font-size:1.125rem; font-weight:700; color:#fff; margin-bottom:0.5rem;">Signal Dispatched</h3>
          <p style="font-size:0.875rem; color:var(--text-secondary);">The host machine is executing your request...</p>
        </div>
      `;
    }

    try {
      let endpoint = '';
      let payload = { pin: state.sessionToken ? undefined : state.pinBuffer };

      const headers = { 'Content-Type': 'application/json' };
      if (state.sessionToken) {
        headers['X-Session-Token'] = state.sessionToken;
      }

      if (action.type === 'switch-os') {
        endpoint = '/api/power/switch-os';
        payload.target_id = action.targetId || 'windows';
      } else if (action.type === 'reboot') {
        endpoint = '/api/power/reboot';
      } else if (action.type === 'shutdown') {
        endpoint = '/api/power/shutdown';
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        showToast(data.message || 'Power operation executed successfully', 'success', 6000);
        setTimeout(closeModal, 2500);
        checkPowerStatus();
      } else {
        showToast(data.message || 'Power operation failed', 'error', 5000);
        setTimeout(closeModal, 2500);
      }
    } catch (err) {
      console.error('Failed to execute power action:', err);
      showToast('Network error while issuing power action', 'error');
      setTimeout(closeModal, 2500);
    }
  }

  // Clear Staged GRUB Next Entry
  async function clearNextEntryAction() {
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (state.sessionToken) headers['X-Session-Token'] = state.sessionToken;

      const res = await fetch('/api/power/clear-next-entry', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({})
      });

      const data = await res.json();
      if (res.ok) {
        showToast('One-shot boot cleared. System will boot into Linux Server.', 'success', 3500);
        checkPowerStatus();
      } else {
        showToast(data.message || 'Failed to clear next entry', 'error');
      }
    } catch (e) {
      console.error(e);
      showToast('Network error while clearing next entry', 'error');
    }
  }

  // Toggle Session Lock
  function updateLockState(isUnlocked) {
    if (!elements.lockBtn) return;
    if (isUnlocked) {
      elements.lockBtn.classList.add('unlocked');
      elements.lockBtn.innerHTML = `
        ${window.JanusIcons ? window.JanusIcons.get('unlock', 'w-3.5 h-3.5') : ''}
        <span>Unlocked</span>
      `;
    } else {
      elements.lockBtn.classList.remove('unlocked');
      elements.lockBtn.innerHTML = `
        ${window.JanusIcons ? window.JanusIcons.get('lock', 'w-3.5 h-3.5') : ''}
        <span>PIN Guarded</span>
      `;
    }
  }

  function handleLockToggle() {
    if (state.sessionToken) {
      // Lock it
      state.sessionToken = null;
      sessionStorage.removeItem('janus_session_token');
      updateLockState(false);
      showToast('Session locked. PIN required for power actions.', 'info', 2500);
    } else {
      openPinModal({ type: 'unlock_only', label: 'Unlock Session' });
    }
  }

  // ============================================================================
  // Initialization & Event Binding
  // ============================================================================

  async function initApp() {
    // 1. Render all SVG icons across page
    if (window.JanusIcons) {
      window.JanusIcons.renderAll(document);
    }

    // 2. Fetch Initial Config
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        state.config = await res.json();
        if (state.config.server && state.config.server.title) {
          document.title = `${state.config.server.title} — JanusDeck`;
        }
      }
    } catch (e) {
      console.warn('Failed to load initial configuration:', e);
    }

    // 3. Start Telemetry SSE Stream
    initTelemetryStream();

    // 4. Fetch Services & Power Status
    fetchServices();
    checkPowerStatus();

    // 5. Check Session Lock status
    if (state.sessionToken) {
      updateLockState(true);
    }

    // 6. Bind Power Actions
    if (elements.btnSwitchWindows) {
      elements.btnSwitchWindows.addEventListener('click', () => {
        openPinModal({
          type: 'switch-os',
          targetId: 'windows',
          label: 'Switch to Windows 11 Gaming Mode'
        });
      });
    }

    if (elements.btnRebootServer) {
      elements.btnRebootServer.addEventListener('click', () => {
        openPinModal({
          type: 'reboot',
          label: 'Reboot Ubuntu Server'
        });
      });
    }

    if (elements.btnShutdownServer) {
      elements.btnShutdownServer.addEventListener('click', () => {
        openPinModal({
          type: 'shutdown',
          label: 'Graceful Host Shutdown'
        });
      });
    }

    if (elements.btnClearNext) {
      elements.btnClearNext.addEventListener('click', clearNextEntryAction);
    }

    if (elements.btnRefreshServices) {
      elements.btnRefreshServices.addEventListener('click', () => fetchServices(true));
    }

    if (elements.lockBtn) {
      elements.lockBtn.addEventListener('click', handleLockToggle);
    }

    // 7. Modal Controls
    if (elements.btnCloseModal) {
      elements.btnCloseModal.addEventListener('click', closeModal);
    }

    if (elements.btnAbortCountdown) {
      elements.btnAbortCountdown.addEventListener('click', () => {
        if (state.countdownTimer) {
          clearInterval(state.countdownTimer);
          state.countdownTimer = null;
        }
        closeModal();
        showToast('Power action cancelled by user', 'info', 3000);
      });
    }

    // 8. Keypad button clicks
    document.querySelectorAll('.keypad-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const digit = btn.getAttribute('data-digit');
        const action = btn.getAttribute('data-action');

        if (digit !== null) {
          handleKeypadInput(digit);
        } else if (action === 'backspace') {
          handleKeypadBackspace();
        } else if (action === 'clear') {
          handleKeypadClear();
        }
      });
    });

    // 9. Keyboard listener for desktop ergonomics
    window.addEventListener('keydown', (e) => {
      if (!elements.modalOverlay.classList.contains('open')) return;

      if (e.key === 'Escape') {
        if (state.countdownTimer) {
          clearInterval(state.countdownTimer);
          state.countdownTimer = null;
          showToast('Power action aborted', 'info', 2500);
        }
        closeModal();
        return;
      }

      // If in keypad view
      if (elements.pinKeypadView && elements.pinKeypadView.style.display !== 'none') {
        if (/^[0-9]$/.test(e.key)) {
          handleKeypadInput(e.key);
        } else if (e.key === 'Backspace') {
          handleKeypadBackspace();
        } else if (e.key === 'Delete' || e.key === 'c' || e.key === 'C') {
          handleKeypadClear();
        }
      }
    });
  }

  // Kickstart on DOM load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
})();
