#!/usr/bin/env bash
# Unity Acquire (User Acquisition) API 连通性与上传测试脚本
#
# 用法:
#   export UNITY_KEY_ID="your-key-id"
#   export UNITY_SECRET_KEY="your-secret-key"
#   export UNITY_ORG_ID="1375631575107"
#   export UNITY_CAMPAIGN_SET_ID="68f60802872bd4a7a9d50071"
#   ./test_unity_acquire.sh              # 仅测连通性（list apps / list creatives）
#   ./test_unity_acquire.sh upload       # 上传 test.mp4（竖版视频）
#   ./test_unity_acquire.sh upload /path/to/video.mp4 landscape

set -euo pipefail

BASE_URL="https://services.api.unity.com/advertise/v1"
ORG_ID="${UNITY_ORG_ID:-1375631575107}"
CAMPAIGN_SET_ID="${UNITY_CAMPAIGN_SET_ID:-68f60802872bd4a7a9d50071}"

if [[ -z "${UNITY_KEY_ID:-}" || -z "${UNITY_SECRET_KEY:-}" ]]; then
  echo "错误: 请设置 UNITY_KEY_ID 和 UNITY_SECRET_KEY 环境变量"
  exit 1
fi

AUTH_HEADER="Authorization: Basic $(printf '%s' "${UNITY_KEY_ID}:${UNITY_SECRET_KEY}" | base64 | tr -d '\n')"

step() {
  echo ""
  echo "========== $1 =========="
}

print_response() {
  local body_file="$1"
  local http_code="$2"
  echo "[HTTP ${http_code}]"
  if [[ ! -s "${body_file}" ]]; then
    echo "(empty body)"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool "${body_file}" 2>/dev/null || cat "${body_file}"
  else
    cat "${body_file}"
  fi
}

api_request() {
  local label="$1"
  local url="$2"
  shift 2
  step "${label}"
  local body_file http_code
  body_file="$(mktemp)"
  http_code="$(curl -sS -o "${body_file}" -w '%{http_code}' -H "${AUTH_HEADER}" "$@" "${url}" || echo '000')"
  print_response "${body_file}" "${http_code}"
  rm -f "${body_file}"
}

api_request "Step 1: List Apps（可选；无 org 级权限时可能 403）" \
  "${BASE_URL}/organizations/${ORG_ID}/apps?limit=10"

api_request "Step 2: List Creatives（验证 KeyID/Secret + 上传权限，campaign set = ${CAMPAIGN_SET_ID})" \
  "${BASE_URL}/organizations/${ORG_ID}/apps/${CAMPAIGN_SET_ID}/creatives?limit=10"

if [[ "${1:-}" == "upload" ]]; then
  FILE="${2:-../../test.mp4}"
  ORIENTATION="${3:-portrait}"

  if [[ ! -f "${FILE}" ]]; then
    echo "错误: 文件不存在: ${FILE}"
    exit 1
  fi

  BASENAME="$(basename "${FILE}")"
  CREATIVE_NAME="api-test-$(date +%Y%m%d-%H%M%S)"

  if [[ "${ORIENTATION}" == "landscape" ]]; then
    CREATIVE_INFO="{\"name\":\"${CREATIVE_NAME}\",\"language\":\"en\",\"landscapeVideo\":{\"fileName\":\"${BASENAME}\"}}"
    FILE_FIELD="landscapeVideoFile"
  else
    CREATIVE_INFO="{\"name\":\"${CREATIVE_NAME}\",\"language\":\"en\",\"video\":{\"fileName\":\"${BASENAME}\"}}"
    FILE_FIELD="videoFile"
  fi

  step "Step 3: Upload Creative (${ORIENTATION} video: ${FILE})"
  body_file="$(mktemp)"
  http_code="$(curl -sS -o "${body_file}" -w '%{http_code}' \
    -X POST \
    -H "${AUTH_HEADER}" \
    -F "creativeInfo=${CREATIVE_INFO};type=application/json" \
    -F "${FILE_FIELD}=@${FILE}" \
    "${BASE_URL}/organizations/${ORG_ID}/apps/${CAMPAIGN_SET_ID}/creatives" || echo '000')"
  print_response "${body_file}" "${http_code}"
  rm -f "${body_file}"
  echo ""
  echo "上传后素材会进入人工审核（moderation），可在 Unity Dashboard Creatives 页查看状态。"
fi

echo ""
echo "完成。Step 1 若 403 但 Step 2 为 200，说明凭证有效且具备 creatives/上传权限（无 list apps 权限属正常）。"
