#!/bin/sh
set -eu
mkdir -p /backups
pg_dump "$DATABASE_URL" -Fc -f "/backups/privateclub_$(date +%Y%m%d_%H%M%S).dump"
find /backups -name '*.dump' -mtime +14 -delete
