"""Safety tests for bounded non-sensitive E2E diagnostics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from foreman_e2e.diagnostics import (
    capture_failure,
    create_test_directory,
    finalize_driver_log,
    safe_current_location,
)


class FakeDriver:
    current_url = (
        "http://127.0.0.1:38123/projects"
        "?token=private-secret#projects"
    )

    def __init__(self) -> None:
        self.scripts: list[str] = []

    def execute_script(self, script: str, *args: object) -> object:
        self.scripts.append(script)

        if "visiblePageCount" in script:
            return {
                "route": "#projects",
                "readyState": "complete",
                "connectionState": "online",
                "bodyFlags": ["dialog-open", "private-class"],
                "visiblePageCount": 1,
                "visibleDialogCount": 1,
                "dirtyFormCount": 1,
                "updateNoticeVisible": False,
            }

        return None

    def get_log(self, _kind: str) -> list[dict[str, str]]:
        return [
            {
                "level": "SEVERE" if index % 2 else "INFO",
                "message": (
                    "Private project at /home/owner/project "
                    "with token=private-secret"
                ),
            }
            for index in range(120)
        ]

    def save_screenshot(self, path: str) -> bool:
        Path(path).write_bytes(b"redacted-screenshot")
        return True


class DiagnosticSafetyTests(unittest.TestCase):
    def test_location_discards_query_values_and_external_origins(self) -> None:
        self.assertEqual(
            safe_current_location(
                "http://127.0.0.1:38123/projects"
                "?secret=value#projects"
            ),
            "/projects#projects",
        )
        self.assertEqual(
            safe_current_location(
                "https://example.com/private#projects"
            ),
            "unavailable",
        )

    def test_directory_name_is_reduced_to_a_safe_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = create_test_directory(
                Path(temporary),
                "run-one",
                "test name /home/owner/private",
            )

            self.assertEqual(
                directory.name,
                "test-name-home-owner-private",
            )

    def test_failure_capture_contains_only_allowlisted_evidence(self) -> None:
        private_values = (
            "private-secret",
            "/home/owner",
            "Private project",
            "Sensitive assertion value",
        )

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            driver = FakeDriver()

            capture_failure(
                driver,
                directory,
                test_name="suite.test_private_failure",
                error=RuntimeError(
                    "Sensitive assertion value at /data/foreman.db"
                ),
            )

            metadata_text = (
                directory / "failure.json"
            ).read_text(encoding="utf-8")
            metadata = json.loads(metadata_text)

            for private_value in private_values:
                self.assertNotIn(private_value, metadata_text)

            self.assertNotIn("visibleText", metadata)
            self.assertNotIn("browserLog", metadata)
            self.assertNotIn("error", metadata)
            self.assertEqual(
                metadata["location"],
                "/projects#projects",
            )
            self.assertEqual(
                metadata["pageState"]["route"],
                "#projects",
            )
            self.assertEqual(
                metadata["pageState"]["bodyFlags"],
                ["dialog-open"],
            )
            self.assertEqual(
                metadata["browserLogSummary"]["capturedEntries"],
                100,
            )
            self.assertTrue(
                metadata["browserLogSummary"]["truncated"]
            )
            self.assertEqual(
                metadata["screenshot"],
                "failure.png",
            )
            self.assertTrue(
                (directory / "failure.png").is_file()
            )
            self.assertGreaterEqual(len(driver.scripts), 3)

    def test_driver_log_is_replaced_by_an_aggregate_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            log_path = directory / "geckodriver.log"
            log_path.write_text(
                "INFO private request /home/owner/file\n"
                "ERROR token=private-secret /data/foreman.db\n",
                encoding="utf-8",
            )

            finalize_driver_log(directory)

            summary = log_path.read_text(encoding="utf-8")

            self.assertIn(
                "Foreman E2E geckodriver summary",
                summary,
            )
            self.assertIn('"rawContentRetained": false', summary)
            self.assertNotIn("/home/owner", summary)
            self.assertNotIn("/data/foreman.db", summary)
            self.assertNotIn("private-secret", summary)
            self.assertIn('"INFO": 1', summary)
            self.assertIn('"ERROR": 1', summary)


if __name__ == "__main__":
    unittest.main()
