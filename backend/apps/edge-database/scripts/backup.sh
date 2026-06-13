#!/bin/bash
# Description: Automated backup script for Edge Database
set -e

BACKUP_DIR="/var/backups/sentinel_edge"
DB_NAME="sentinel_edge"
DB_USER="sentinel_admin"
DATE=$(date +"%Y%m%d_%H%M%S")

mkdir -p $BACKUP_DIR

echo "Starting backup of database $DB_NAME..."
pg_dump -U $DB_USER -d $DB_NAME -F c -f "$BACKUP_DIR/${DB_NAME}_${DATE}.dump"

echo "Backup complete: $BACKUP_DIR/${DB_NAME}_${DATE}.dump"
# Keep only last 7 days of backups
find $BACKUP_DIR -type f -name "*.dump" -mtime +7 -delete
echo "Old backups cleaned up."
