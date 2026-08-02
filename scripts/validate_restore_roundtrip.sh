#!/usr/bin/env bash
set -euo pipefail

repository_root="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"
cd "$repository_root"

image_ref="foreman-restore-roundtrip:validation-$$"

cleanup() {
    docker image rm -f "$image_ref" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker build --tag "$image_ref" backend

docker run --rm \
    --network none \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,size=256m \
    --security-opt no-new-privileges:true \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --env FOREMAN_DATABASE_URL=sqlite:////tmp/foreman-restore-roundtrip.db \
    "$image_ref" \
    python -m unittest \
    tests.test_recovery_roundtrip.RecoveryRoundTripApiTests
