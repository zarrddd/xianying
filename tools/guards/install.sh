#!/bin/sh
# 安装显影泄露门到本仓库 .git/hooks（克隆后必须重跑一次）
cd "$(dirname "$0")/../.." || exit 1
for h in pre-commit commit-msg pre-push; do
  cp "tools/guards/$h" ".git/hooks/$h" && chmod +x ".git/hooks/$h" || exit 1
done
echo "[GUARD] installed: pre-commit commit-msg pre-push"
