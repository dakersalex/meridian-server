#!/bin/bash
launchctl unload /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.plist 2>/dev/null
sleep 1
launchctl load /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.plist
sleep 3
curl -s http://localhost:4242/api/health
