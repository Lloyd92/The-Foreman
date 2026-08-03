"""Fail-closed control of the disposable E2E deployment network."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import REPOSITORY_ROOT, validate_origin


COMPOSE_FILE = (REPOSITORY_ROOT / "compose.e2e.yaml").resolve()
SAFE_PROJECT_NAME = re.compile(
    r"^foreman-e2e-[a-z0-9][a-z0-9_-]{5,120}$"
)
SAFE_CONTAINER_ID = re.compile(r"^[a-f0-9]{12,64}$")


class DisposableDeploymentError(RuntimeError):
    """Raised when disposable deployment isolation cannot be proven."""


@dataclass(frozen=True)
class DisposableDeploymentConfig:
    """Validated identifiers for the current disposable deployment."""

    project_name: str
    compose_file: Path
    origin: str

    @property
    def internal_network(self) -> str:
        return f"{self.project_name}_e2e"

    @classmethod
    def from_environment(
        cls,
        environment: dict[str, str] | None = None,
    ) -> "DisposableDeploymentConfig":
        values = dict(
            os.environ if environment is None else environment
        )

        if values.get("FOREMAN_E2E_RUNTIME") != "1":
            raise DisposableDeploymentError(
                "Disposable deployment control requires E2E runtime mode."
            )

        project_name = values.get(
            "FOREMAN_E2E_COMPOSE_PROJECT",
            "",
        ).strip()

        if not SAFE_PROJECT_NAME.fullmatch(project_name):
            raise DisposableDeploymentError(
                "The disposable Compose project name is missing or unsafe."
            )

        raw_compose_file = values.get(
            "FOREMAN_E2E_COMPOSE_FILE",
            "",
        ).strip()

        if not raw_compose_file:
            raise DisposableDeploymentError(
                "The disposable Compose file is missing."
            )

        compose_file = Path(raw_compose_file).expanduser().resolve()

        if compose_file != COMPOSE_FILE:
            raise DisposableDeploymentError(
                "Deployment control requires the repository E2E Compose file."
            )

        origin = validate_origin(
            values.get("FOREMAN_E2E_ORIGIN", "")
        )

        return cls(
            project_name=project_name,
            compose_file=compose_file,
            origin=origin,
        )


class DisposableDeployment:
    """Temporarily sever only frontend-to-backend E2E connectivity."""

    def __init__(
        self,
        config: DisposableDeploymentConfig,
    ) -> None:
        self.config = config

    def _run(self, command: list[str]) -> str:
        result = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise DisposableDeploymentError(
                f"Disposable Docker command failed: "
                f"{' '.join(command[:3])}; "
                f"{result.stderr.strip() or 'no error output'}"
            )

        return result.stdout.strip()

    def _compose(self, *arguments: str) -> str:
        return self._run([
            "docker",
            "compose",
            "--project-name",
            self.config.project_name,
            "--file",
            str(self.config.compose_file),
            *arguments,
        ])

    def _service_container_id(self, service: str) -> str:
        output = self._compose("ps", "-q", service)
        container_ids = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        if (
            len(container_ids) != 1
            or not SAFE_CONTAINER_ID.fullmatch(container_ids[0])
        ):
            raise DisposableDeploymentError(
                f"Expected exactly one safe {service} container."
            )

        return container_ids[0]

    def _inspect(self, kind: str, identifier: str) -> dict[str, Any]:
        output = self._run([
            "docker",
            kind,
            "inspect",
            identifier,
        ])

        try:
            payload = json.loads(output)
        except json.JSONDecodeError as error:
            raise DisposableDeploymentError(
                f"Docker {kind} inspection was not valid JSON."
            ) from error

        if not isinstance(payload, list) or len(payload) != 1:
            raise DisposableDeploymentError(
                f"Docker {kind} inspection was ambiguous."
            )

        record = payload[0]

        if not isinstance(record, dict):
            raise DisposableDeploymentError(
                f"Docker {kind} inspection was malformed."
            )

        return record

    def _validate_container(
        self,
        container_id: str,
        service: str,
    ) -> dict[str, Any]:
        record = self._inspect("container", container_id)
        labels = record.get("Config", {}).get("Labels") or {}

        if (
            labels.get("com.docker.compose.project")
            != self.config.project_name
            or labels.get("com.docker.compose.service") != service
        ):
            raise DisposableDeploymentError(
                f"The {service} container failed Compose label validation."
            )

        networks = (
            record.get("NetworkSettings", {}).get("Networks") or {}
        )

        if not isinstance(networks, dict):
            raise DisposableDeploymentError(
                f"The {service} network attachment is malformed."
            )

        return networks

    def _validate_boundary(self) -> tuple[str, dict[str, Any]]:
        network = self._inspect(
            "network",
            self.config.internal_network,
        )
        labels = network.get("Labels") or {}

        if (
            labels.get("com.docker.compose.project")
            != self.config.project_name
            or labels.get("com.docker.compose.network") != "e2e"
            or network.get("Internal") is not True
        ):
            raise DisposableDeploymentError(
                "The internal E2E network failed isolation validation."
            )

        frontend_id = self._service_container_id("frontend")
        backend_id = self._service_container_id("backend")

        frontend_networks = self._validate_container(
            frontend_id,
            "frontend",
        )
        backend_networks = self._validate_container(
            backend_id,
            "backend",
        )

        if self.config.internal_network not in backend_networks:
            raise DisposableDeploymentError(
                "The disposable backend is not on the internal E2E network."
            )

        return frontend_id, frontend_networks

    def disconnect_frontend_from_backend(self) -> None:
        frontend_id, networks = self._validate_boundary()

        if self.config.internal_network not in networks:
            return

        self._run([
            "docker",
            "network",
            "disconnect",
            self.config.internal_network,
            frontend_id,
        ])

        _, updated_networks = self._validate_boundary()

        if self.config.internal_network in updated_networks:
            raise DisposableDeploymentError(
                "Frontend remained connected to the internal E2E network."
            )

    def reconnect_frontend_to_backend(self) -> None:
        frontend_id, networks = self._validate_boundary()

        if self.config.internal_network in networks:
            return

        self._run([
            "docker",
            "network",
            "connect",
            self.config.internal_network,
            frontend_id,
        ])

        _, updated_networks = self._validate_boundary()

        if self.config.internal_network not in updated_networks:
            raise DisposableDeploymentError(
                "Frontend did not reconnect to the internal E2E network."
            )
