"""Base unittest support for Foreman Firefox E2E workflows."""

from __future__ import annotations

import unittest

from .browser import firefox_session
from .config import HarnessConfig
from .diagnostics import capture_failure


class BrowserE2ETestCase(unittest.TestCase):
    """Own one fresh Firefox WebDriver session per browser test."""

    config: HarnessConfig

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.config = HarnessConfig.from_environment()

    def setUp(self) -> None:
        super().setUp()
        self._session_context = firefox_session(
            self.config,
            test_name=self.id(),
        )
        self.session = self._session_context.__enter__()
        self.driver = self.session.driver

    def tearDown(self) -> None:
        result = getattr(
            getattr(self, "_outcome", None),
            "result",
            None,
        )
        failures = []

        if result is not None:
            failures.extend(
                pair
                for pair in result.failures
                if pair[0] is self
            )
            failures.extend(
                pair
                for pair in result.errors
                if pair[0] is self
            )

        if failures:
            self.session.mark_failed()
            capture_failure(
                self.driver,
                self.session.directory,
                test_name=self.id(),
            )

        self._session_context.__exit__(None, None, None)
        super().tearDown()
