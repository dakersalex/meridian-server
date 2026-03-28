#!/bin/bash
# Meridian wake-and-sync script
# Runs on Mac wake, triggers Playwright scrapers via the local Flask API
# Logs to ~/meridian-server/logs/wake_sync.log

LOG="$HOME/meridian-server/logs/wake_sync.log"
API="http://localhost:4242"

echo "$(date): Wake sync triggered" >> "$LOG"

# Wait for Flask to be ready (it should already be running via launchd)
for i in {1..12}; do
    if curl -s "$API/api/health" > /dev/null 2>&1; then
        break
    fi
    echo "$(date): Waiting for Flask... ($i)" >> "$LOG"
    sleep 5
done

# Trigger sync for all sources
echo "$(date): Triggering sync" >> "$LOG"
curl -s -X POST "$API/api/sync" \
  -H "Content-Type: application/json" \
  -d '{"sources":["ft","economist","fa"]}' >> "$LOG" 2>&1

echo "$(date): Sync triggered, waiting 90s for completion" >> "$LOG"
sleep 90

# Trigger enrichment of title-only articles
echo "$(date): Triggering enrichment" >> "$LOG"
curl -s -X POST "$API/api/enrich-title-only" >> "$LOG" 2>&1

echo "$(date): Wake sync complete" >> "$LOG"
