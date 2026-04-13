
# Trigger AI pick — scrapes FT/Economist/FA recommendation feeds, Sonnet scores
# Waits for Playwright profiles to be free after the main scrape above
echo "$(date): Waiting 5 min for scrape profiles to clear before AI pick..." >> "$LOG"
sleep 300
echo "$(date): Triggering AI pick feed scrape" >> "$LOG"
curl -s -X POST "$API/api/ai-pick" \
  -H "Content-Type: application/json" \
  -d '{}' >> "$LOG" 2>&1

echo "$(date): Wake sync complete" >> "$LOG"
