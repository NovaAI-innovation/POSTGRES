#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

self_lower="$(printf '%s' "$SCRIPT_PATH" | tr '[:upper:]' '[:lower:]')"
if [[ "$self_lower" == *"claude"* ]]; then
  TARGET="$ROOT_DIR/scripts/gateway/agents/claude.sh"
elif [[ "$self_lower" == *"codex"* ]]; then
  TARGET="$ROOT_DIR/scripts/gateway/agents/codex.sh"
else
  target_agent="${GATEWAY_AGENT:-codex}"
  target_agent="$(printf '%s' "$target_agent" | tr '[:upper:]' '[:lower:]')"
  if [[ "$target_agent" == "claude" ]]; then
    TARGET="$ROOT_DIR/scripts/gateway/agents/claude.sh"
  else
    TARGET="$ROOT_DIR/scripts/gateway/agents/codex.sh"
  fi
fi

if [[ ! -f "$TARGET" ]]; then
  echo "Gateway wrapper not found: $TARGET" >&2
  exit 1
fi

exec bash "$TARGET" "$@"