#!/usr/bin/env bash
# 从 conf.yaml 导出 Unity 环境变量（需 conf.yaml 使用下方推荐格式）
#
# 推荐 conf.yaml 格式:
#   UNITY_CONFIG:
#     key_id: 700a10c3-93da-4605-9ca4-494f08de2871
#     secret_key: your-secret
#     organization_id: "1375631575107"
#     campaign_set_id: 68f60802872bd4a7a9d50071

set -euo pipefail

CONF="${1:-../conf.yaml}"

if [[ ! -f "${CONF}" ]]; then
  echo "找不到 ${CONF}" >&2
  exit 1
fi

# 简单解析（仅支持推荐格式的 key: value）
export UNITY_KEY_ID="$(grep -E '^\s+key_id:' "${CONF}" | head -1 | sed 's/.*key_id:\s*//' | tr -d ' \"')"
export UNITY_SECRET_KEY="$(grep -E '^\s+secret_key:' "${CONF}" | head -1 | sed 's/.*secret_key:\s*//' | tr -d ' \"')"
export UNITY_ORG_ID="$(grep -E '^\s+organization_id:' "${CONF}" | head -1 | sed 's/.*organization_id:\s*//' | tr -d ' \"')"
export UNITY_CAMPAIGN_SET_ID="$(grep -E '^\s+campaign_set_id:' "${CONF}" | head -1 | sed 's/.*campaign_set_id:\s*//' | tr -d ' \"')"

echo "UNITY_KEY_ID=${UNITY_KEY_ID}"
echo "UNITY_ORG_ID=${UNITY_ORG_ID}"
echo "UNITY_CAMPAIGN_SET_ID=${UNITY_CAMPAIGN_SET_ID}"
echo "(secret_key 已加载，未打印)"
