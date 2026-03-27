#!/bin/bash
# Meridian deploy script — commits, pushes, pulls on VPS, restarts service
set -e

cd "$(dirname "$0")"

# Commit message from arg or default
MSG="${1:-Deploy}"

echo "📦 Committing and pushing..."
git add -A
git commit -m "$MSG" || echo "Nothing to commit"
git push

echo "🚀 Deploying to VPS..."
ssh root@204.168.179.158 "cd /opt/meridian-server && git pull && systemctl restart meridian && echo '✅ Done'"

echo "✅ Deploy complete"
