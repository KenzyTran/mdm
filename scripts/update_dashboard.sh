#!/bin/bash
# One-command: re-export data + deploy to S3
#
# Usage:
#   bash scripts/update_dashboard.sh
#   bash scripts/update_dashboard.sh my-custom-bucket-name

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Step 1: Exporting dashboard data..."
uv run python "$SCRIPT_DIR/export_dashboard_data.py"

echo ""
echo "Step 2: Deploying to S3..."
bash "$SCRIPT_DIR/deploy_dashboard.sh" "${1:-mdm-trading-dashboard}"
