#!/bin/bash
# VPS-native wake sync — runs RSS picks + newsletter ingestion on VPS.
# Mirrors the 05:40 + 11:40 Geneva schedule of the Mac wake_and_sync.sh

set -a
source /etc/meridian/secrets.env
set +a

LOG=/var/log/meridian/wake_sync.log
mkdir -p /var/log/meridian
API=http://localhost:4242

echo "$(date -u): ==VPS Wake sync triggered==" >> "$LOG"

# 1. RSS-based AI pick
echo "$(date -u): Running RSS AI pick" >> "$LOG"
curl -s -X POST "$API/api/rss-pick" >> "$LOG" 2>&1
echo "" >> "$LOG"

# 2. Newsletter sync from iCloud
echo "$(date -u): Syncing newsletters from iCloud" >> "$LOG"
curl -s -X POST "$API/api/newsletters/sync" >> "$LOG" 2>&1
echo "" >> "$LOG"

# 3. Health check
echo "$(date -u): Health check" >> "$LOG"
curl -s "$API/api/health/enrichment" >> "$LOG" 2>&1
echo "" >> "$LOG"

echo "$(date -u): ==VPS Wake sync complete==" >> "$LOG"
echo "" >> "$LOG"
