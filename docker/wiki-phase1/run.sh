#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose_file="${project_dir}/compose.yml"

cleanup() {
  docker compose --file "${compose_file}" down --volumes --remove-orphans
}
trap cleanup EXIT

docker compose --file "${compose_file}" build --pull
docker compose --file "${compose_file}" up --detach --wait
docker compose --file "${compose_file}" exec --no-TTY frappe \
  env/bin/python /opt/wiki-phase1/verify.py

# Bench's Procfile must still contain the shared infrastructure processes.
docker compose --file "${compose_file}" top frappe | grep -E 'schedule|worker'
docker compose --file "${compose_file}" top frappe | grep -E 'socketio|9000'

docker compose --file "${compose_file}" exec --no-TTY frappe \
  bench --site wiki-phase1.localhost migrate
