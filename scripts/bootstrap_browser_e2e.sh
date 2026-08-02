#!/usr/bin/env bash
set -euo pipefail

repository_root="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"
cd "$repository_root"

venv_directory="$repository_root/.venv-e2e"
python_binary="${PYTHON_BINARY:-python3}"

command -v "$python_binary" >/dev/null 2>&1 || {
    echo "Python 3 is required." >&2
    exit 1
}

"$python_binary" -m venv "$venv_directory"

"$venv_directory/bin/python" -m pip \
    --disable-pip-version-check \
    install \
    --requirement "$repository_root/e2e/requirements.txt"

"$venv_directory/bin/python" - <<'PY'
import selenium
print(f"Browser E2E environment ready: Selenium {selenium.__version__}")
PY
