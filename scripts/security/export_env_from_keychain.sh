#!/usr/bin/env bash
set -euo pipefail

# Export env vars from macOS Keychain into current shell.
# Usage:
#   source scripts/security/export_env_from_keychain.sh
#
# Optional:
#   export SERVICE_PREFIX=wechat-ai-service

SERVICE_PREFIX="${SERVICE_PREFIX:-wechat-ai-service}"

read_secret() {
  local key="$1"
  /usr/bin/security find-generic-password \
    -a "$USER" \
    -s "${SERVICE_PREFIX}.${key}" \
    -w
}

export COZE_API_TOKEN="$(read_secret coze_api_token)"
export COZE_WORKFLOW_API="$(read_secret coze_workflow_api)"
export COZE_WORKFLOW_PROJECT_ID="$(read_secret coze_workflow_project_id)"
export AI_USER_AGENT_TOKEN="$(read_secret ai_user_agent_token)"
export AI_USER_AGENT_API="$(read_secret ai_user_agent_api)"
export AI_USER_AGENT_PROJECT_ID="$(read_secret ai_user_agent_project_id)"
export TEST_EMAIL_IMAP_HOST="$(read_secret test_email_imap_host)"
export TEST_EMAIL_IMAP_PORT="$(read_secret test_email_imap_port)"
export TEST_EMAIL_IMAP_USERNAME="$(read_secret test_email_imap_username)"
export TEST_EMAIL_IMAP_PASSWORD="$(read_secret test_email_imap_password)"
export TEST_EMAIL_IMAP_MAILBOX="$(read_secret test_email_imap_mailbox)"

export ENABLE_EMAIL_CHECK="true"
export REQUIRE_EMAIL_CHECK="true"

echo "Loaded env vars from Keychain service prefix: ${SERVICE_PREFIX}.*"
