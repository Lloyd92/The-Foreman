"""Readiness retry tests for the isolated browser harness."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from foreman_e2e.wait_for_health import wait_for_health


class FakeHealthResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return b'{"status":"healthy","database":"online"}'


class HealthReadinessTests(unittest.TestCase):
    def test_transient_connection_reset_is_retried(self) -> None:
        responses = [
            ConnectionResetError("frontend still starting"),
            FakeHealthResponse(),
        ]

        def fake_urlopen(*args, **kwargs):
            result = responses.pop(0)

            if isinstance(result, BaseException):
                raise result

            return result

        with (
            patch(
                "foreman_e2e.wait_for_health.urlopen",
                side_effect=fake_urlopen,
            ),
            patch("foreman_e2e.wait_for_health.time.sleep"),
        ):
            payload = wait_for_health(
                "http://127.0.0.1:38123",
                timeout_seconds=5,
                interval_seconds=0,
            )

        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["database"], "online")
        self.assertEqual(responses, [])


if __name__ == "__main__":
    unittest.main()
