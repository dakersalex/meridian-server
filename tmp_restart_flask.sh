#!/bin/bash
sleep 1
pkill -f server.py 2>/dev/null
sleep 2
cd /Users/alexdakers/meridian-server
python3 server.py >> logs/server.log 2>&1 &
