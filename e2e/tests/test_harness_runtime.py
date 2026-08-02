"""Minimal runtime proof for the Firefox/WebDriver harness."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.base import BrowserE2ETestCase


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Runtime harness test requires the disposable deployment runner.",
)
class HarnessRuntimeTests(BrowserE2ETestCase):
    def test_firefox_reaches_the_isolated_origin(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.get(self.config.origin)

        WebDriverWait(
            self.driver,
            self.config.timeout_seconds,
        ).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        self.assertEqual(
            self.driver.capabilities.get("browserName"),
            "firefox",
        )
        self.assertTrue(
            self.driver.current_url.startswith(self.config.origin)
        )


if __name__ == "__main__":
    unittest.main()
