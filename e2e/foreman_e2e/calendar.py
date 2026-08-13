"""Stable browser interactions for Calendar workflows."""

from __future__ import annotations

from typing import Any


class CalendarPage:
    def __init__(
        self,
        driver: Any,
        *,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.timeout_seconds = timeout_seconds

    def set_date(self, value: str) -> None:
        element = self.driver.find_element("id", "calendar-date")
        self.driver.execute_script(
            """
            const element = arguments[0];
            const value = arguments[1];
            element.value = value;
            element.dispatchEvent(new Event("change", {bubbles: true}));
            """,
            element,
            value,
        )

    def _wait_for_dialog(self, dialog_id: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: driver.find_element(
                "id",
                dialog_id,
            ).is_displayed()
        )

    def create_entry(
        self,
        *,
        title: str,
        start_at: str,
        end_at: str,
    ) -> None:
        self.driver.find_element("id", "add-calendar-entry").click()
        self._wait_for_dialog("calendar-entry-dialog-backdrop")

        title_input = self.driver.find_element(
            "id",
            "calendar-entry-title",
        )
        title_input.clear()
        title_input.send_keys(title)

        for element_id, value in (
            ("calendar-entry-start-at", start_at),
            ("calendar-entry-end-at", end_at),
        ):
            element = self.driver.find_element("id", element_id)
            self.driver.execute_script(
                """
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(
                    new Event("input", {bubbles: true})
                );
                arguments[0].dispatchEvent(
                    new Event("change", {bubbles: true})
                );
                """,
                element,
                value,
            )

        self.driver.find_element(
            "css selector",
            "#calendar-entry-form button[type='submit']",
        ).click()

        self.wait_for_row(title)

    def create_weekly_routine(
        self,
        *,
        title: str,
        anchor_date: str,
        weekday: str,
        start_time: str,
    ) -> None:
        self.driver.find_element("id", "add-calendar-routine").click()
        self._wait_for_dialog("calendar-routine-dialog-backdrop")

        title_input = self.driver.find_element(
            "id",
            "calendar-routine-title",
        )
        title_input.send_keys(title)

        frequency = self.driver.find_element(
            "id",
            "calendar-routine-frequency",
        )
        self.driver.execute_script(
            """
            arguments[0].value = "weekly";
            arguments[0].dispatchEvent(new Event("change", {bubbles: true}));
            """,
            frequency,
        )

        self.driver.find_element(
            "css selector",
            f'#calendar-routine-weekdays input[value="{weekday}"]',
        ).click()

        for element_id, value in (
            ("calendar-routine-anchor-date", anchor_date),
            ("calendar-routine-start-time", start_time),
        ):
            element = self.driver.find_element("id", element_id)
            self.driver.execute_script(
                """
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(
                    new Event("input", {bubbles: true})
                );
                arguments[0].dispatchEvent(
                    new Event("change", {bubbles: true})
                );
                """,
                element,
                value,
            )

        self.driver.find_element(
            "css selector",
            "#calendar-routine-form button[type='submit']",
        ).click()

        self.wait_for_row(title)

    def find_row(self, title: str) -> Any | None:
        for row in self.driver.find_elements(
            "css selector",
            "#calendar-table-body tr",
        ):
            names = row.find_elements(
                "css selector",
                ".resource-record-name",
            )
            if names and names[0].text == title:
                return row

        return None

    def wait_for_row(self, title: str) -> Any:
        from selenium.webdriver.support.ui import WebDriverWait

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(lambda _driver: self.find_row(title) or False)
