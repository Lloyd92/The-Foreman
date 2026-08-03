"""Intentional browser failure used only by the diagnostic proof."""

from __future__ import annotations

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase


CONTROLLED_SECRET = (
    "FOREMAN-CONTROLLED-PRIVATE-DIAGNOSTIC-VALUE"
)


class ControlledFailureFixture(BrowserE2ETestCase):
    def test_controlled_browser_failure(self) -> None:
        app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )
        app.open("projects")

        self.driver.execute_script(
            """
            const marker = document.createElement("div");
            marker.id = "controlled-private-marker";
            marker.textContent = arguments[0];
            document.body.appendChild(marker);
            console.error(arguments[0]);
            """,
            CONTROLLED_SECRET,
        )

        self.fail(
            CONTROLLED_SECRET +
            " at /home/owner/private and /data/foreman.db"
        )
