"""Explicit acceptance checks for the disposable browser deployment."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import REPOSITORY_ROOT, validate_origin
from .deployment import (
    SAFE_PROJECT_NAME,
    DisposableDeploymentConfig,
)


COLLECTION_ENDPOINTS = (
    "/api/inventory",
    "/api/projects",
    "/api/tasks",
    "/api/work-dependencies",
)


class CleanDeploymentAcceptanceError(RuntimeError):
    """Raised when clean deployment acceptance cannot be proven."""


def verify_clean_collections(
    origin: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> dict[str, int]:
    """Require every persisted operational collection to begin empty."""

    approved_origin = validate_origin(origin)
    open_request = opener or urlopen
    counts: dict[str, int] = {}

    for endpoint in COLLECTION_ENDPOINTS:
        request = Request(
            f"{approved_origin}{endpoint}",
            headers={"Accept": "application/json"},
        )

        try:
            with open_request(request, timeout=5) as response:
                if response.status != 200:
                    raise CleanDeploymentAcceptanceError(
                        f"{endpoint} returned HTTP {response.status}."
                    )

                payload = json.loads(
                    response.read().decode("utf-8")
                )
        except (
            HTTPError,
            URLError,
            OSError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            raise CleanDeploymentAcceptanceError(
                f"{endpoint} could not prove a clean collection "
                f"({type(error).__name__})."
            ) from error

        if not isinstance(payload, list):
            raise CleanDeploymentAcceptanceError(
                f"{endpoint} did not return a collection."
            )

        counts[endpoint] = len(payload)

        if payload:
            raise CleanDeploymentAcceptanceError(
                f"{endpoint} was not empty "
                f"({len(payload)} record(s))."
            )

    return counts


def verify_project_cleanup(
    project_name: str,
    *,
    runner: Callable[..., Any] | None = None,
) -> dict[str, int]:
    """Prove no resources remain for the approved Compose project."""

    if not SAFE_PROJECT_NAME.fullmatch(project_name):
        raise CleanDeploymentAcceptanceError(
            "Cleanup verification requires a safe E2E project name."
        )

    run_command = runner or subprocess.run
    commands = {
        "containers": [
            "docker",
            "ps",
            "-aq",
            "--filter",
            f"label=com.docker.compose.project={project_name}",
        ],
        "networks": [
            "docker",
            "network",
            "ls",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project_name}",
        ],
        "images": [
            "docker",
            "image",
            "ls",
            "-q",
            "--filter",
            f"reference={project_name}-*",
        ],
    }
    counts: dict[str, int] = {}

    for resource_type, command in commands.items():
        result = run_command(
            command,
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise CleanDeploymentAcceptanceError(
                f"Docker {resource_type} inspection failed."
            )

        identifiers = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        counts[resource_type] = len(identifiers)

        if identifiers:
            raise CleanDeploymentAcceptanceError(
                f"Disposable {resource_type} remain after cleanup "
                f"({len(identifiers)} found)."
            )

    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=("clean-state", "cleanup"),
    )
    arguments = parser.parse_args()
    config = DisposableDeploymentConfig.from_environment()

    if arguments.phase == "clean-state":
        verify_clean_collections(config.origin)
        print(
            "Clean deployment verified: "
            "Inventory=0; Projects=0; Tasks=0; "
            "WorkDependencies=0."
        )
        return

    verify_project_cleanup(config.project_name)
    print(
        "Disposable cleanup verified: "
        "containers=0; networks=0; images=0."
    )


if __name__ == "__main__":
    main()
