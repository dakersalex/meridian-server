#!/bin/bash
# Backup Mac meridian.db to VPS daily
# Installed as launchd job: com.alexdakers.meridian.dbbackup
# Runs at 23:00 daily

MAC_DB="/Users/alexdakers/meridian-server/meridian.db"
VPS="root@204.168.179.158"
BACKUP_DIR="/opt/meridian-server/db_backups"
DATE=$(date +%Y-%m-%d)

# Create backup dir on VPS if needed
ssh $VPS "mkdir -p $BACKUP_DIR"

# Copy Mac DB to VPS with date stamp
scp "$MAC_DB" "$VPS:$BACKUP_DIR/meridian_mac_$DATE.db"

# Keep only last 7 days of backups
ssh $VPS "ls -t $BACKUP_DIR/meridian_mac_*.db | tail -n +8 | xargs rm -f 2>/dev/null; echo 'Backups kept:'; ls -lh $BACKUP_DIR/"

echo "DB backup complete: meridian_mac_$DATE.db"
