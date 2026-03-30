#!/bin/bash
# Deploy MDM dashboard to S3 static website
#
# Usage:
#   bash scripts/deploy_dashboard.sh
#   bash scripts/deploy_dashboard.sh my-custom-bucket-name

set -euo pipefail

BUCKET="${1:-mdm-trading-dashboard}"
REGION="ap-southeast-1"
DASHBOARD_DIR="$(cd "$(dirname "$0")/../dashboard" && pwd)"

echo "============================================================"
echo "MDM DASHBOARD S3 DEPLOYMENT"
echo "============================================================"
echo "Bucket: $BUCKET"
echo "Region: $REGION"
echo "Source: $DASHBOARD_DIR"
echo ""

# 1. Create bucket (ignore if already exists)
echo "[1/5] Creating S3 bucket..."
if aws s3 ls "s3://$BUCKET" 2>/dev/null; then
    echo "  Bucket already exists."
else
    aws s3 mb "s3://$BUCKET" --region "$REGION"
    echo "  Bucket created."
fi

# 2. Disable block public access
echo "[2/5] Configuring public access..."
aws s3api put-public-access-block --bucket "$BUCKET" \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# 3. Enable static website hosting
echo "[3/5] Enabling static website hosting..."
aws s3 website "s3://$BUCKET" --index-document index.html --error-document index.html

# 4. Set public read policy
echo "[4/5] Setting bucket policy..."
aws s3api put-bucket-policy --bucket "$BUCKET" --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
        \"Sid\": \"PublicReadGetObject\",
        \"Effect\": \"Allow\",
        \"Principal\": \"*\",
        \"Action\": \"s3:GetObject\",
        \"Resource\": \"arn:aws:s3:::${BUCKET}/*\"
    }]
}"

# 5. Sync files
echo "[5/5] Uploading files..."
aws s3 sync "$DASHBOARD_DIR" "s3://$BUCKET/" \
    --delete \
    --cache-control "max-age=300"

echo ""
echo "============================================================"
echo "DEPLOYMENT COMPLETE"
echo ""
echo "URL: http://${BUCKET}.s3-website-${REGION}.amazonaws.com"
echo "============================================================"
