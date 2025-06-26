#!/usr/bin/env bash
set -euo pipefail

# Usage: sudo deploy.sh <SERVICE_NAME> [BRANCH]
if [[ $# -lt 1 ]]; then
  echo "Usage: sudo $0 <SERVICE_NAME> [BRANCH]" >&2
  exit 1
fi

SVC="$1"
BRANCH="${2:-main}"
DIR="/opt/$SVC"

echo "🔄 Pulling latest code for $SVC (branch: $BRANCH)..."
cd "$DIR"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "🛠 Installing new dependencies..."
cd "$DIR/Backend" && . venv/bin/activate && pip install -r requirements.txt

echo "🔁 Restarting service $SVC..."
systemctl restart "$SVC"

echo "✅ Deployment complete for $SVC"
echo "⚡ Now showing logs—^C to exit"
journalctl -fu DIY-MOD
