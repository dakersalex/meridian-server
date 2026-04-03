#!/bin/bash
# Detached Flask restart — safe to run via shell endpoint
sleep 1
launchctl unload ~/Library/LaunchAgents/com.alexdakers.meridian.plist 2>/dev/null
sleep 2
launchctl load ~/Library/LaunchAgents/com.alexdakers.meridian.plist
