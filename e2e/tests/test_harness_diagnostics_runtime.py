"""Runtime proof of the actual failed-test diagnostic lifecycle."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from foreman_e2e.config import HarnessConfig
from foreman_e2e.diagnostics import sanitize_identifier
from fixtures.controlled_failure import CONTROLLED_SECRET


FIXTURE_TEST_ID = (
    "fixtures.controlled_failure."
    "ControlledFailureFixture."
    "test_controlled_browser_failure"
)


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Controlled failure proof requires the disposable deployment runner.",
)
class DiagnosticRuntimeProofTests(unittest.TestCase):
    def test_controlled_failure_retains_only_safe_evidence(self) -> None:
        config = HarnessConfig.from_environment()
        repository_root = Path(__file__).resolve().parents[2]
        artifact_directory = (
            config.artifacts_root
            / config.run_id
            / sanitize_identifier(FIXTURE_TEST_ID)
        )

        self.assertFalse(
            artifact_directory.exists(),
            "Controlled fixture artifact directory already exists.",
        )

        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(
            repository_root / "e2e"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                FIXTURE_TEST_ID,
            ],
            cwd=repository_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )

        try:
            self.assertNotEqual(
                result.returncode,
                0,
                "The controlled fixture did not fail as required.",
            )

            metadata_path = (
                artifact_directory / "failure.json"
            )
            screenshot_path = (
                artifact_directory / "failure.png"
            )
            driver_log_path = (
                artifact_directory / "geckodriver.log"
            )

            self.assertTrue(metadata_path.is_file())
            self.assertTrue(screenshot_path.is_file())
            self.assertTrue(driver_log_path.is_file())

            metadata_text = metadata_path.read_text(
                encoding="utf-8"
            )
            metadata = json.loads(metadata_text)
            driver_log = driver_log_path.read_text(
                encoding="utf-8"
            )
            screenshot = screenshot_path.read_bytes()

            forbidden_values = (
                CONTROLLED_SECRET,
                "/home/owner/private",
                "/data/foreman.db",
            )

            for forbidden in forbidden_values:
                self.assertNotIn(forbidden, metadata_text)
                self.assertNotIn(forbidden, driver_log)
                self.assertNotIn(
                    forbidden.encode("utf-8"),
                    screenshot,
                )

            self.assertNotIn("visibleText", metadata)
            self.assertNotIn("browserLog", metadata)
            self.assertNotIn("error", metadata)
            self.assertEqual(
                metadata["pageState"]["route"],
                "#projects",
            )
            self.assertEqual(
                metadata["screenshot"],
                "failure.png",
            )

            self.assertIn(
                "Foreman E2E geckodriver summary",
                driver_log,
            )
            self.assertIn(
                '"rawContentRetained": false',
                driver_log,
            )

            self.assertFalse(
                (artifact_directory / "page-source.html").exists()
            )
            self.assertLess(
                len(metadata_text.encode("utf-8")),
                50_000,
            )
            self.assertLess(len(screenshot), 5_000_001)
            self.assertLess(
                len(driver_log.encode("utf-8")),
                50_000,
            )
        finally:
            shutil.rmtree(
                artifact_directory,
                ignore_errors=True,
            )


if __name__ == "__main__":
    unittest.main()
