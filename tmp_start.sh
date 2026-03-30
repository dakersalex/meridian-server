#!/bin/bash
# Start Flask server manually if not running
cd /Users/alexdakers/meridian-server
if ! curl -s http://localhost:4242/api/health > /dev/null 2>&1; then
    echo "Starting Flask..."
    nohup /usr/bin/python3 server.py > logs/server.log 2>&1 &
    echo "PID: $!"
else
    echo "Flask already running"
fi
