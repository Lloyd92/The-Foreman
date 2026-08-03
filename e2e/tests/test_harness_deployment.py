"""Safety tests for disposable E2E deployment control."""

from __future__ import annotations

import unittest
from pathlib import Path

from foreman_e2e.config import REPOSITORY_ROOT
from foreman_e2e.deployment import (
    COMPOSE_FILE,
    DisposableDeploymentConfig,
    DisposableDeploymentError,
)


def valid_environment() -> dict[str, str]:
    return {
        "FOREMAN_E2E_RUNTIME": "1",
        "FOREMAN_E2E_COMPOSE_PROJECT":
            "foreman-e2e-20260802t191400z-12345",
        "FOREMAN_E2E_COMPOSE_FILE": str(COMPOSE_FILE),
        "FOREMAN_E2E_ORIGIN": "http://127.0.0.1:38123",
    }


class DisposableDeploymentConfigurationTests(unittest.TestCase):
    def test_accepts_only_the_current_disposable_boundary(self) -> None:
        config = DisposableDeploymentConfig.from_environment(
            valid_environment()
        )

        self.assertEqual(
            config.project_name,
            "foreman-e2e-20260802t191400z-12345",
        )
        self.assertEqual(
            config.internal_network,
            "foreman-e2e-20260802t191400z-12345_e2e",
        )
        self.assertEqual(config.compose_file, COMPOSE_FILE)

    def test_rejects_non_runtime_use(self) -> None:
        environment = valid_environment()
        environment["FOREMAN_E2E_RUNTIME"] = "0"

        with self.assertRaises(DisposableDeploymentError):
            DisposableDeploymentConfig.from_environment(environment)

    def test_rejects_live_or_ambiguous_project_names(self) -> None:
        for project_name in (
            "",
            "foreman",
            "foreman_default",
            "foreman-e2e",
            "Foreman-E2E-test",
            "other-e2e-project",
        ):
            with self.subTest(project_name=project_name):
                environment = valid_environment()
                environment[
                    "FOREMAN_E2E_COMPOSE_PROJECT"
                ] = project_name

                with self.assertRaises(DisposableDeploymentError):
                    DisposableDeploymentConfig.from_environment(
                        environment
                    )

    def test_rejects_any_other_compose_file(self) -> None:
        environment = valid_environment()
        environment["FOREMAN_E2E_COMPOSE_FILE"] = str(
            Path(REPOSITORY_ROOT) / "compose.yaml"
        )

        with self.assertRaises(DisposableDeploymentError):
            DisposableDeploymentConfig.from_environment(environment)


if __name__ == "__main__":
    unittest.main()
