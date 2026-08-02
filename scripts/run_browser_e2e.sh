#!/usr/bin/env bash
set -euo pipefail

repository_root="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"
cd "$repository_root"

venv_python="$repository_root/.venv-e2e/bin/python"
compose_file="$repository_root/compose.e2e.yaml"

for command in docker firefox geckodriver; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "Required command is unavailable: $command" >&2
        exit 1
    }
done

if [[ ! -x "$venv_python" ]]; then
    echo "Browser E2E environment is missing." >&2
    echo "Run ./scripts/bootstrap_browser_e2e.sh first." >&2
    exit 1
fi

choose_port() {
    python3 - <<'PY'
import socket

with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    print(listener.getsockname()[1])
PY
}

port="${FOREMAN_E2E_PORT:-$(choose_port)}"

if [[ ! "$port" =~ ^[0-9]+$ ]] ||
   (( port < 1024 || port > 65535 )) ||
   [[ "$port" == "3000" || "$port" == "5000" ]]; then
    echo "Unsafe FOREMAN_E2E_PORT: $port" >&2
    exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_id="run-${timestamp}-$$"
project_name="foreman-e2e-${timestamp,,}-$$"
resolved_config="$(mktemp)"
compose=(
    docker compose
    --project-name "$project_name"
    --file "$compose_file"
)

cleanup() {
    "${compose[@]}" down \
        --remove-orphans \
        --rmi local >/dev/null 2>&1 || true
    rm -f "$resolved_config"
}
trap cleanup EXIT INT TERM

export FOREMAN_E2E_PORT="$port"
export FOREMAN_E2E_ORIGIN="http://127.0.0.1:$port"
export FOREMAN_E2E_RUN_ID="$run_id"
export FOREMAN_E2E_ARTIFACTS_ROOT="$repository_root/artifacts/e2e"
export FOREMAN_E2E_RUNTIME=1

"${compose[@]}" config --format json > "$resolved_config"

PYTHONPATH="$repository_root/e2e" \
    "$venv_python" -m foreman_e2e.isolation \
    --config "$resolved_config" \
    --project "$project_name" \
    --port "$port"

"${compose[@]}" up --detach --build

PYTHONPATH="$repository_root/e2e" \
    "$venv_python" -m foreman_e2e.wait_for_health

PYTHONPATH="$repository_root/e2e" \
    "$venv_python" -m unittest discover \
    --start-directory "$repository_root/e2e/tests" \
    --pattern 'test_*.py'
