"""Clean-startup and navigation smoke coverage."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import (
    ROUTE_HEADINGS,
    ForemanApplication,
)
from foreman_e2e.base import BrowserE2ETestCase


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Startup smoke tests require the disposable deployment runner.",
)
class StartupNavigationTests(BrowserE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )

    def assert_route_heading(
        self,
        route: str,
        expected_heading: str,
    ) -> None:
        actual_heading = self.app.heading(route)

        if route == "dashboard":
            self.assertTrue(
                actual_heading.endswith(expected_heading),
                f"Unexpected dashboard greeting: {actual_heading!r}",
            )
            return

        self.assertEqual(actual_heading, expected_heading)

    def test_operational_dashboard_reports_release_identity(self) -> None:
        self.app.open()

        gate = self.driver.find_element(
            "id",
            "hardhead-availability",
        )

        self.assertFalse(gate.is_displayed())
        self.assertEqual(
            gate.get_attribute("data-connection-state"),
            "online",
        )
        self.assertEqual(
            self.app.text_by_id("system-status"),
            "System online",
        )
        self.assertEqual(
            self.app.text_by_id("api-status"),
            "ONLINE",
        )
        self.assertEqual(self.app.text_by_id("version"), "0.7.5")
        self.assertEqual(
            self.app.text_by_id("footer-version"),
            "0.7.5",
        )
        # Mutating browser modules share this disposable database.
        # Release and operational checks must not depend on test order.
        self.assertEqual(self.app.visible_routes(), ["dashboard"])
        self.assertEqual(self.app.active_route(), "dashboard")

    def test_sidebar_navigation_reaches_every_route(self) -> None:
        self.app.open()

        for route, expected_heading in ROUTE_HEADINGS.items():
            with self.subTest(route=route):
                self.app.navigate(route)

                self.assertEqual(self.app.visible_routes(), [route])
                self.assertEqual(self.app.active_route(), route)
                self.assertEqual(
                    self.driver.execute_script(
                        "return window.location.hash"
                    ),
                    f"#{route}",
                )
                self.assert_route_heading(
                    route,
                    expected_heading,
                )

    def test_direct_deep_links_initialize_every_route(self) -> None:
        for route, expected_heading in ROUTE_HEADINGS.items():
            with self.subTest(route=route):
                self.app.open(route)

                self.assertEqual(self.app.visible_routes(), [route])
                self.assertEqual(self.app.active_route(), route)
                self.assert_route_heading(
                    route,
                    expected_heading,
                )

    def test_unknown_route_falls_back_to_dashboard(self) -> None:
        self.app.open(
            "not-a-real-route",
            expected_route="dashboard",
        )

        self.assertEqual(self.app.visible_routes(), ["dashboard"])
        self.assertEqual(self.app.active_route(), "dashboard")
        self.assert_route_heading(
            "dashboard",
            ROUTE_HEADINGS["dashboard"],
        )


if __name__ == "__main__":
    unittest.main()
