#!/usr/bin/env bash
set -euo pipefail

# Save test credentials into macOS Keychain.
# Usage:
#   1) Export env vars first, then run this script.
#   2) Or pass --from-file /path/to/env_file

SERVICE_PREFIX="${SERVICE_PREFIX:-wechat-ai-service}"

load_from_file() {
  local env_file="$1"
  if [[ ! -f "$env_file" ]]; then
    echo "env file not found: $env_file" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  set -a && source "$env_file" && set +a
}

if [[ "${1:-}" == "--from-file" ]]; then
  load_from_file "${2:-}"
fi

required_vars=(
  COZE_API_TOKEN
  COZE_WORKFLOW_API
  COZE_WORKFLOW_PROJECT_ID
  AI_USER_AGENT_TOKEN
  AI_USER_AGENT_API
  AI_USER_AGENT_PROJECT_ID
  TEST_EMAIL_IMAP_HOST
  TEST_EMAIL_IMAP_PORT
  TEST_EMAIL_IMAP_USERNAME
  TEST_EMAIL_IMAP_PASSWORD
  TEST_EMAIL_IMAP_MAILBOX
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "missing env: $var" >&2
    exit 1
  fi
done

save_secret() {
  local key="$1"
  local value="$2"
  /usr/bin/security add-generic-password \
    -a "$USER" \
    -s "${SERVICE_PREFIX}.${key}" \
    -w "$value" \
    -U >/dev/null
}

save_secret "coze_api_token" "$COZE_API_TOKEN"
save_secret "coze_workflow_api" "$COZE_WORKFLOW_API"
save_secret "coze_workflow_project_id" "$COZE_WORKFLOW_PROJECT_ID"
save_secret "ai_user_agent_token" "$AI_USER_AGENT_TOKEN"
save_secret "ai_user_agent_api" "$AI_USER_AGENT_API"
save_secret "ai_user_agent_project_id" "$AI_USER_AGENT_PROJECT_ID"
save_secret "test_email_imap_host" "$TEST_EMAIL_IMAP_HOST"
save_secret "test_email_imap_port" "$TEST_EMAIL_IMAP_PORT"
save_secret "test_email_imap_username" "$TEST_EMAIL_IMAP_USERNAME"
save_secret "test_email_imap_password" "$TEST_EMAIL_IMAP_PASSWORD"
save_secret "test_email_imap_mailbox" "$TEST_EMAIL_IMAP_MAILBOX"

echo "Saved secrets to Keychain service prefix: ${SERVICE_PREFIX}.*"
