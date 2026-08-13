"""v0.8.3 Calendar browser compatibility acceptance."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.calendar import CalendarPage
from foreman_e2e.spaces import SpacesControl


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Calendar acceptance requires the disposable deployment runner.",
)
class CalendarAcceptanceTests(BrowserE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.calendar = CalendarPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.spaces = SpacesControl(
            self.driver,
            self.app,
            timeout_seconds=self.config.timeout_seconds,
        )

    def test_fixed_and_recurring_calendar_facts(self) -> None:
        self.app.open("calendar")
        space_id = self.spaces.active_space_id()

        self.app.api_request(
            "/api/calendar/settings",
            method="PUT",
            headers={"X-Foreman-Space-Id": space_id},
            body={"timezoneName": "America/New_York"},
        )

        self.app.open("calendar")
        self.calendar.set_date("2026-08-13")

        self.calendar.create_entry(
            title="E2E Calendar Commitment",
            start_at="2026-08-13T08:00",
            end_at="2026-08-13T09:00",
        )

        row = self.calendar.wait_for_row(
            "E2E Calendar Commitment"
        )
        self.assertIn("commitment", row.text.lower())

        self.calendar.create_weekly_routine(
            title="E2E Weekly Routine",
            anchor_date="2026-08-13",
            weekday="thursday",
            start_time="10:00",
        )

        routine = self.calendar.wait_for_row(
            "E2E Weekly Routine"
        )
        self.assertIn("edit routine", routine.text.lower())
        self.assertIn("skip this date", routine.text.lower())

        self.assertIn(
            "Calendar does not decide Work feasibility.",
            self.driver.find_element(
                "css selector",
                '[data-page="calendar"]',
            ).text,
        )


if __name__ == "__main__":
    unittest.main()
