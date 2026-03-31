#!/bin/bash
launchctl unload /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.plist 2>/dev/null
sleep 2
launchctl load /Users/alexdakers/Library/LaunchAgents/com.alexdakers.meridian.plist
echo "Flask restarted at $(date)" >> /tmp/restart_flask.log
