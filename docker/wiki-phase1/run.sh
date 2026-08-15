#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
compose_file="${project_dir}/compose.yml"
repo_dir="$(cd "${project_dir}/../.." && pwd)"
export CRM_COMMIT="${CRM_COMMIT:-$(git -C "${repo_dir}" rev-parse HEAD)}"

cleanup() {
	status=$?
	if [[ "${status}" -ne 0 ]]; then
		docker compose --file "${compose_file}" logs --no-color || true
	fi
	docker compose --file "${compose_file}" down --volumes --remove-orphans
	exit "${status}"
}
trap cleanup EXIT

docker compose --file "${compose_file}" build --pull
docker compose --file "${compose_file}" up --detach --wait
docker compose --file "${compose_file}" exec --no-TTY frappe \
  env/bin/python /opt/wiki-phase1/verify.py

# The production-like Procfile must keep all required application processes.
docker compose --file "${compose_file}" top frappe | grep -E 'schedule|worker'
docker compose --file "${compose_file}" top frappe | grep -E 'socketio|9000'

docker compose --file "${compose_file}" exec --no-TTY frappe \
  bench --site wiki-phase1.localhost migrate
