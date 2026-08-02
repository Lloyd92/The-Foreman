"""Fail-closed validation for the disposable E2E Compose contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_DATABASE_URL = "sqlite:////tmp/foreman-e2e.db"
FORBIDDEN_TEXT = (
    "foreman-data",
    "caddy-data",
    "caddy-config",
    "/data/foreman.db",
    "192.168.1.184",
)


class IsolationContractError(RuntimeError):
    """Raised when resolved Compose configuration is not disposable."""


def _fail(message: str) -> None:
    raise IsolationContractError(message)


def _environment(service: dict[str, Any]) -> dict[str, str]:
    environment = service.get("environment", {})

    if isinstance(environment, dict):
        return {
            str(key): "" if value is None else str(value)
            for key, value in environment.items()
        }

    if isinstance(environment, list):
        result: dict[str, str] = {}

        for item in environment:
            key, _, value = str(item).partition("=")
            result[key] = value

        return result

    _fail("Service environment has an unsupported shape.")


def _tmpfs_targets(service: dict[str, Any]) -> set[str]:
    result: set[str] = set()

    for entry in service.get("tmpfs", []) or []:
        if isinstance(entry, str):
            result.add(entry.split(":", 1)[0])
        elif isinstance(entry, dict):
            target = entry.get("target")
            if target:
                result.add(str(target))

    return result


def _network_names(service: dict[str, Any]) -> set[str]:
    networks = service.get("networks", {})

    if isinstance(networks, dict):
        return {str(name) for name in networks}

    if isinstance(networks, list):
        return {str(name) for name in networks}

    _fail("Service networks have an unsupported shape.")


def validate_compose_contract(
    config: dict[str, Any],
    *,
    expected_project: str,
    expected_port: int,
) -> None:
    """Reject any resolved deployment that could touch live Foreman state."""

    if config.get("name") != expected_project:
        _fail("Resolved Compose project name does not match the E2E run.")

    services = config.get("services")

    if not isinstance(services, dict):
        _fail("Resolved Compose services are missing.")

    if set(services) != {"backend", "frontend"}:
        _fail("E2E Compose must contain only backend and frontend services.")

    if config.get("volumes"):
        _fail("E2E Compose must not define named or external volumes.")

    serialized = json.dumps(config, sort_keys=True)

    for token in FORBIDDEN_TEXT:
        if token in serialized:
            _fail(f"Resolved Compose contains forbidden token: {token}")

    for service_name, service in services.items():
        if not isinstance(service, dict):
            _fail(f"Service {service_name} has an invalid definition.")

        if service.get("container_name"):
            _fail("E2E services must not use fixed container names.")

        if service.get("volumes"):
            _fail("E2E services must not mount volumes or host paths.")

        if service.get("privileged"):
            _fail("E2E services must not be privileged.")

        if service.get("devices"):
            _fail("E2E services must not attach host devices.")

        if service.get("network_mode") == "host":
            _fail("E2E services must not use the host network.")

        if service.get("pid") == "host" or service.get("ipc") == "host":
            _fail("E2E services must not join host process namespaces.")

    backend = services["backend"]
    backend_environment = _environment(backend)

    if (
        backend_environment.get("FOREMAN_DATABASE_URL")
        != EXPECTED_DATABASE_URL
    ):
        _fail("E2E backend database must be the approved temporary SQLite path.")

    if backend.get("read_only") is not True:
        _fail("E2E backend root filesystem must be read-only.")

    if "/tmp" not in _tmpfs_targets(backend):
        _fail("E2E backend must receive an ephemeral /tmp tmpfs.")

    frontend = services["frontend"]
    ports = frontend.get("ports", []) or []

    if len(ports) != 1 or not isinstance(ports[0], dict):
        _fail("E2E frontend must publish exactly one resolved port.")

    port = ports[0]

    try:
        published = int(port.get("published"))
        target = int(port.get("target"))
    except (TypeError, ValueError) as error:
        raise IsolationContractError(
            "E2E frontend has an invalid resolved port."
        ) from error

    if (
        port.get("host_ip") != "127.0.0.1"
        or published != expected_port
        or target != 80
        or port.get("protocol", "tcp") != "tcp"
    ):
        _fail("E2E frontend port is not the approved loopback binding.")

    backend_networks = _network_names(backend)

    if backend_networks != {"e2e"}:
        _fail("E2E backend must remain only on the internal network.")

    frontend_networks = _network_names(frontend)

    if frontend_networks != {"e2e", "edge"}:
        _fail(
            "E2E frontend must join only the internal and loopback-edge "
            "networks."
        )

    networks = config.get("networks")

    if not isinstance(networks, dict):
        _fail("E2E Compose networks are missing.")

    if set(networks) != {"e2e", "edge"}:
        _fail("E2E Compose must define exactly e2e and edge networks.")

    internal_network = networks["e2e"]
    edge_network = networks["edge"]

    if (
        not isinstance(internal_network, dict)
        or internal_network.get("internal") is not True
    ):
        _fail("E2E backend network must be internal.")

    if (
        not isinstance(edge_network, dict)
        or edge_network.get("internal", False) is not False
        or edge_network.get("driver") != "bridge"
    ):
        _fail("E2E edge network must be a non-internal bridge.")


def validate_config_file(
    path: Path,
    *,
    expected_project: str,
    expected_port: int,
) -> None:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IsolationContractError(
            "Resolved Compose configuration could not be read."
        ) from error

    if not isinstance(config, dict):
        _fail("Resolved Compose configuration must be a JSON object.")

    validate_compose_contract(
        config,
        expected_project=expected_project,
        expected_port=expected_port,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--port", type=int, required=True)
    arguments = parser.parse_args()

    validate_config_file(
        arguments.config,
        expected_project=arguments.project,
        expected_port=arguments.port,
    )
    print("Disposable E2E Compose contract verified.")


if __name__ == "__main__":
    main()
