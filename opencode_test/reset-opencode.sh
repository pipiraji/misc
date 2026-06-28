#!/usr/bin/env bash
set -euo pipefail

# OpenCode Full Reset
echo "⚠ OpenCode Full Reset"
echo "이 스크립트는 모든 opencode 관련 데이터를 삭제합니다."
read -rp "계속하시겠습니까? (y/N): " confirm
if [ "${confirm,,}" != "y" ]; then
  echo "취소됨."
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Global config
if [ -d "$HOME/.config/opencode" ]; then
  rm -rf "$HOME/.config/opencode"
  echo "✓ ~/.config/opencode 삭제됨"
fi

# 2. State
if [ -d "$HOME/.local/state/opencode" ]; then
  rm -rf "$HOME/.local/state/opencode"
  echo "✓ ~/.local/state/opencode 삭제됨"
fi

# 3. Share data (DB, logs)
if [ -d "$HOME/.local/share/opencode" ]; then
  rm -rf "$HOME/.local/share/opencode"
  echo "✓ ~/.local/share/opencode 삭제됨"
fi

# 4. Cache
if [ -d "$HOME/.cache/opencode" ]; then
  rm -rf "$HOME/.cache/opencode"
  echo "✓ ~/.cache/opencode 삭제됨"
fi

# 5. Project node_modules
if [ -f "$SCRIPT_DIR/package.json" ]; then
  for pkg in opencode-ai oh-my-opencode oh-my-openagent; do
    if [ -d "$SCRIPT_DIR/node_modules/$pkg" ]; then
      rm -rf "$SCRIPT_DIR/node_modules/$pkg"
      echo "✓ node_modules/$pkg 삭제됨"
    fi
  done
fi

echo "✅ OpenCode 전체 리셋 완료."
echo "재설치하려면: npm install"
