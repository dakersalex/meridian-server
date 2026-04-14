#!/bin/bash
lsof -ti tcp:4242 | xargs kill -9 2>/dev/null
sleep 2
launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist
echo "Flask restarted"
sleep 3
curl -s http://localhost:4242/api/health
