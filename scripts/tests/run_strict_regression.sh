#!/usr/bin/env bash
set -euo pipefail

# 严格回归执行入口：
# 1) 从 Keychain 加载环境变量
# 2) 强制开启邮件校验
# 3) 运行 AI User Agent 集成测试

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "scripts/security/export_env_from_keychain.sh" ]]; then
  echo "缺少 scripts/security/export_env_from_keychain.sh" >&2
  exit 2
fi

# Best effort: refresh Coze CLI access token before loading env.
if command -v coze >/dev/null 2>&1; then
  coze auth status >/dev/null 2>&1 || true
fi

# shellcheck disable=SC1091
source scripts/security/export_env_from_keychain.sh
export ENABLE_EMAIL_CHECK="true"
export REQUIRE_EMAIL_CHECK="true"

RUN_ID="${1:-strict_$(date +%Y%m%d_%H%M%S)}"
MAX_TURNS="${MAX_TURNS:-8}"

echo "运行严格回归：run_id=${RUN_ID}, max_turns=${MAX_TURNS}"
python3 src/tests/ai_user_integration_test.py --max-turns "${MAX_TURNS}" --run-id "${RUN_ID}"
