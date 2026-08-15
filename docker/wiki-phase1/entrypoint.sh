#!/usr/bin/env bash
set -euo pipefail

site="${PHASE1_SITE:-wiki-phase1.localhost}"
admin_password="${PHASE1_ADMIN_PASSWORD:-admin}"
db_root_password="${PHASE1_DB_ROOT_PASSWORD:-phase1-root}"

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

if [[ ! -f "sites/${site}/site_config.json" ]]; then
  bench new-site "${site}" \
    --mariadb-root-password "${db_root_password}" \
    --admin-password "${admin_password}" \
    --no-mariadb-socket
  bench --site "${site}" install-app crm
  bench --site "${site}" install-app wiki
  bench --site "${site}" migrate
  bench --site "${site}" set-config developer_mode 1
  bench --site "${site}" set-config mute_emails 1
fi

bench use "${site}"
exec bench start --procfile /opt/wiki-phase1/Procfile
