# syntax=docker/dockerfile:1
# ==============================================================================
# JanusDeck: Production Dockerfile
# Multi-Arch Ready: linux/amd64, linux/arm64
# Multi-Stage Build: Node.js (Svelte 5) -> Python 3.12-slim-bookworm runtime
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Svelte 5 SPA Frontend Builder
# ------------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Minimal Python 3.12 Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="JanusDeck" \
      org.opencontainers.image.description="Command deck and mobile dashboard for hybrid gaming & dual-boot home servers" \
      org.opencontainers.image.authors="Project Janus Contributors" \
      org.opencontainers.image.licenses="MIT"

# Avoid buffering and bytecode generation
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# Install host bridge utilities & healthcheck probe
# - grub-common: provides grub-editenv to manipulate /boot/grub/grubenv
# - dbus: provides dbus-send for fallback login1 method calls
# - curl: used for container healthcheck probe
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        grub-common \
        dbus \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script and application assets
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY config.example.yaml /app/config.example.yaml
COPY src/ /app/src/
# Copy compiled Svelte 5 SPA from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

EXPOSE 8080

# Container healthcheck against local endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
