---
phase: 22-combined-integration-validation
plan: 02
subsystem: dashboard
tags: [dashboard, export, liquidity-overlay, s3-deploy]

# Dependency graph
requires:
  - phase: 22-combined-integration-validation
    plan: 01
    provides: Combined validation results confirming filter interactions

# Key files
key-files:
  modified:
    - scripts/export_dashboard_data.py
    - dashboard/index.html
  created:
    - dashboard/data/mdm_v2_filtered.json
    - dashboard/data/liquidity_overlay.json

# Self-Check: PASSED
---

## What was done

### Task 1: Extended dashboard export with V2 filtered model and liquidity overlay
- Added `export_v2_filtered_model()` to `scripts/export_dashboard_data.py` — runs MDMV2Engine with all filters ON (QE floor, sell acceleration, buy filter, buy confirmation)
- Added `export_liquidity_overlay()` — exports 988 Global Liquidity data points and 33 QE floor active zones from `data/global_liquidity.csv`
- New model `mdm_v2_filtered` produces: total return 93.7%, CAGR 6.1%, max DD -41.5%, 66 trades
- Liquidity overlay includes `data` (line chart values) and `qe_zones` (shaded region date ranges)

### Task 2: Dashboard review and simplification
- Human review revealed V2 + All Filters (93.7%) underperforms V2 default (190.8%) on VN30
- Root cause: QE Floor designed for US markets — Fed liquidity has low correlation with VN30
- **Decision:** Removed underperforming tabs (V2 Filtered, Hybrid, Phase 15) from dashboard UI
- Kept only V2 State Machine (best performer: 190.8%, -31.8% DD)
- Added QE zone overlay plugin to equity charts (green shaded bands)
- Code and data files preserved for reference

### S3 Deploy
- AWS session expired during deploy — user to re-authenticate and run `bash scripts/deploy_dashboard.sh`

## Deviations
- Dashboard simplified to single model instead of 4 tabs — user decision based on performance review
- S3 deploy deferred pending AWS re-authentication

## What's next
- User re-authenticates AWS and deploys: `bash scripts/deploy_dashboard.sh`
