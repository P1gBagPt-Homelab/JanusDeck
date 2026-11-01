#!/usr/bin/env bash
# ==============================================================================
# JanusDeck: Coolify Automatic Redeploy Trigger
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present
if [ -f "${ROOT_DIR}/.env" ]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
fi

COOLIFY_HOST="${COOLIFY_HOST:-http://192.168.1.68:8000}"
COOLIFY_UUID="${COOLIFY_UUID:-rvi8hu1owmes3shdpsiuyz3q}"
COOLIFY_TOKEN="${COOLIFY_TOKEN:-}"

if [ -z "${COOLIFY_TOKEN}" ]; then
  echo "❌ Error: COOLIFY_TOKEN is not set. Please set it in .env or as an environment variable."
  exit 1
fi

echo "🚀 Triggering Coolify redeploy for Janus Deck on ${COOLIFY_HOST}..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}" \
  -H "Content-Type: application/json" \
  "${COOLIFY_HOST}/api/v1/deploy?uuid=${COOLIFY_UUID}&force=false")

HTTP_STATUS=$(echo "${RESPONSE}" | tail -n1)
BODY=$(echo "${RESPONSE}" | sed '$d')

if [ "${HTTP_STATUS}" -eq 200 ]; then
  echo "✅ Deployment successfully queued on Coolify!"
  echo "📦 Response: ${BODY}"
else
  echo "❌ Coolify deployment failed with HTTP ${HTTP_STATUS}"
  echo "Response: ${BODY}"
  exit 1
fi
