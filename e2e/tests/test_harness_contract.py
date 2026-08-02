"""Safety-contract tests for the isolated Firefox E2E harness."""

from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path

from foreman_e2e.config import (
    HarnessConfig,
    HarnessConfigurationError,
    validate_origin,
)
from foreman_e2e.isolation import (
    EXPECTED_DATABASE_URL,
    IsolationContractError,
    validate_compose_contract,
)


def valid_compose_config(
    *,
    project: str = "foreman-e2e-test",
    port: int = 38123,
) -> dict:
    return {
        "name": project,
        "services": {
            "backend": {
                "build": {"context": "/repository/backend"},
                "environment": {
                    "FOREMAN_DATABASE_URL": EXPECTED_DATABASE_URL,
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                "read_only": True,
                "restart": "no",
                "tmpfs": [
                    "/tmp:rw,nosuid,nodev,noexec,size=268435456"
                ],
                "networks": {"e2e": None},
            },
            "frontend": {
                "build": {"context": "/repository/frontend"},
                "depends_on": {"backend": {"condition": "service_started"}},
                "restart": "no",
                "ports": [
                    {
                        "host_ip": "127.0.0.1",
                        "target": 80,
                        "published": str(port),
                        "protocol": "tcp",
                        "mode": "ingress",
                    }
                ],
                "networks": {
                    "e2e": None,
                    "edge": None,
                },
            },
        },
        "networks": {
            "e2e": {
                "name": f"{project}_e2e",
                "internal": True,
            },
            "edge": {
                "name": f"{project}_edge",
                "driver": "bridge",
                "internal": False,
            },
        },
    }


class HarnessConfigurationTests(unittest.TestCase):
    def test_accepts_only_high_loopback_http_origin(self) -> None:
        self.assertEqual(
            validate_origin("http://127.0.0.1:38123"),
            "http://127.0.0.1:38123",
        )

        for origin in (
            "https://127.0.0.1:38123",
            "http://localhost:38123",
            "http://0.0.0.0:38123",
            "http://192.168.1.184:38123",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000",
            "http://127.0.0.1:80",
            "http://127.0.0.1:38123/dashboard",
        ):
            with self.subTest(origin=origin):
                with self.assertRaises(HarnessConfigurationError):
                    validate_origin(origin)

    def test_environment_configuration_stays_under_artifacts_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "executable"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)

            driver_link = Path(temporary) / "geckodriver"
            driver_link.symlink_to(executable)

            environment = {
                "FOREMAN_E2E_ORIGIN": "http://127.0.0.1:38123",
                "FOREMAN_E2E_RUN_ID": "contract-test",
                "FOREMAN_E2E_FIREFOX_BINARY": str(executable),
                "FOREMAN_E2E_GECKODRIVER_BINARY": str(driver_link),
                "FOREMAN_E2E_ARTIFACTS_ROOT": str(
                    Path(__file__).resolve().parents[2]
                    / "artifacts"
                    / "e2e"
                    / "contract-test"
                ),
            }
            config = HarnessConfig.from_environment(environment)

            self.assertEqual(
                config.geckodriver_binary,
                str(driver_link.absolute()),
            )
            self.assertTrue(
                Path(config.geckodriver_binary).is_symlink()
            )

        self.assertEqual(config.origin, "http://127.0.0.1:38123")
        self.assertTrue(config.headless)
        self.assertFalse(config.keep_artifacts)

    def test_prefers_real_snap_firefox_binary_over_launcher(
        self,
    ) -> None:
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temporary:
            firefox_binary = Path(temporary) / "firefox"
            firefox_binary.write_bytes(b"\x7fELF")
            firefox_binary.chmod(0o755)

            environment = {
                "FOREMAN_E2E_ORIGIN": "http://127.0.0.1:38123",
                "FOREMAN_E2E_RUN_ID": "snap-firefox-test",
                "FOREMAN_E2E_GECKODRIVER_BINARY": "/bin/true",
            }

            with patch(
                "foreman_e2e.config.SNAP_FIREFOX_BINARY",
                firefox_binary,
            ):
                config = HarnessConfig.from_environment(environment)

        self.assertEqual(
            config.firefox_binary,
            str(firefox_binary),
        )

    def test_environment_rejects_unsafe_artifact_location(self) -> None:
        environment = {
            "FOREMAN_E2E_ORIGIN": "http://127.0.0.1:38123",
            "FOREMAN_E2E_RUN_ID": "contract-test",
            "FOREMAN_E2E_FIREFOX_BINARY": "/bin/true",
            "FOREMAN_E2E_GECKODRIVER_BINARY": "/bin/true",
            "FOREMAN_E2E_ARTIFACTS_ROOT": "/tmp/private-e2e",
        }

        with self.assertRaises(HarnessConfigurationError):
            HarnessConfig.from_environment(environment)


class ComposeIsolationTests(unittest.TestCase):
    def assert_rejected(self, config: dict) -> None:
        with self.assertRaises(IsolationContractError):
            validate_compose_contract(
                config,
                expected_project="foreman-e2e-test",
                expected_port=38123,
            )

    def test_approved_contract_passes(self) -> None:
        validate_compose_contract(
            valid_compose_config(),
            expected_project="foreman-e2e-test",
            expected_port=38123,
        )

    def test_rejects_live_database_and_volume(self) -> None:
        live_database = valid_compose_config()
        live_database["services"]["backend"]["environment"][
            "FOREMAN_DATABASE_URL"
        ] = "sqlite:////data/foreman.db"
        self.assert_rejected(live_database)

        live_volume = valid_compose_config()
        live_volume["volumes"] = {"foreman-data": {}}
        live_volume["services"]["backend"]["volumes"] = [
            {
                "type": "volume",
                "source": "foreman-data",
                "target": "/data",
            }
        ]
        self.assert_rejected(live_volume)

    def test_rejects_caddy_or_extra_services(self) -> None:
        config = valid_compose_config()
        config["services"]["caddy"] = {"image": "caddy:latest"}
        self.assert_rejected(config)

    def test_rejects_public_or_live_frontend_binding(self) -> None:
        public = valid_compose_config()
        public["services"]["frontend"]["ports"][0][
            "host_ip"
        ] = "0.0.0.0"
        self.assert_rejected(public)

        live_port = valid_compose_config()
        live_port["services"]["frontend"]["ports"][0][
            "published"
        ] = "3000"
        self.assert_rejected(live_port)

    def test_rejects_noninternal_network(self) -> None:
        config = valid_compose_config()
        config["networks"]["e2e"]["internal"] = False
        self.assert_rejected(config)

    def test_rejects_elevated_host_access(self) -> None:
        for field, value in (
            ("privileged", True),
            ("network_mode", "host"),
            ("pid", "host"),
            ("ipc", "host"),
            ("devices", ["/dev/sda:/dev/sda"]),
        ):
            with self.subTest(field=field):
                config = valid_compose_config()
                config["services"]["backend"][field] = value
                self.assert_rejected(config)

    def test_rejects_backend_on_loopback_edge_network(self) -> None:
        config = valid_compose_config()
        config["services"]["backend"]["networks"]["edge"] = None
        self.assert_rejected(config)

    def test_rejects_internal_loopback_edge_network(self) -> None:
        config = valid_compose_config()
        config["networks"]["edge"]["internal"] = True
        self.assert_rejected(config)

    def test_rejects_fixed_container_names(self) -> None:
        config = valid_compose_config()
        config["services"]["backend"]["container_name"] = "foreman-backend"
        self.assert_rejected(config)


if __name__ == "__main__":
    unittest.main()
