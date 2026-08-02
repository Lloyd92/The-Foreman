"""Stable browser interactions for backend Task workflows."""

from __future__ import annotations

import json
from typing import Any


class TasksPage:
    """Drive visible Task actions and same-origin API inspection."""

    def __init__(
        self,
        driver: Any,
        *,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.timeout_seconds = timeout_seconds

    def create_task(self, title: str, priority: str) -> None:
        from selenium.webdriver.support.ui import Select

        title_input = self.driver.find_element("id", "task-title")
        title_input.clear()
        title_input.send_keys(title)

        Select(
            self.driver.find_element("id", "task-priority")
        ).select_by_value(priority)

        self.driver.find_element(
            "css selector",
            '#task-form button[type="submit"]',
        ).click()

        self.wait_for_row(title)

    def find_row(self, title: str) -> Any | None:
        for row in self.driver.find_elements(
            "css selector",
            "#task-list .task-row",
        ):
            names = row.find_elements(
                "css selector",
                ".task-title",
            )
            if names and names[0].text == title:
                return row
        return None

    def wait_for_row(self, title: str) -> Any:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def locate(_driver: Any) -> Any | bool:
            try:
                return self.find_row(title) or False
            except StaleElementReferenceException:
                return False

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(locate)

    def wait_for_task_absent(self, title: str) -> None:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def absent(_driver: Any) -> bool:
            try:
                return self.find_row(title) is None
            except StaleElementReferenceException:
                return False

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(absent)

    def is_completed(self, title: str) -> bool:
        row = self.wait_for_row(title)
        checkbox = row.find_element(
            "css selector",
            '[data-action="toggle"]',
        )
        classes = (row.get_attribute("class") or "").split()

        return checkbox.is_selected() and "completed" in classes

    def toggle_task(
        self,
        title: str,
        *,
        expected_completed: bool,
    ) -> None:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        row = self.wait_for_row(title)
        row.find_element(
            "css selector",
            '[data-action="toggle"]',
        ).click()

        def reached_expected_state(_driver: Any) -> bool:
            try:
                row_now = self.find_row(title)
                if row_now is None:
                    return False

                checkbox = row_now.find_element(
                    "css selector",
                    '[data-action="toggle"]',
                )
                classes = (
                    row_now.get_attribute("class") or ""
                ).split()

                completed = (
                    checkbox.is_selected()
                    and "completed" in classes
                )
                reopened = (
                    not checkbox.is_selected()
                    and "completed" not in classes
                )

                return (
                    completed
                    if expected_completed
                    else reopened
                )
            except StaleElementReferenceException:
                return False

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(reached_expected_state)

    def delete_task(self, title: str) -> None:
        row = self.wait_for_row(title)
        row.find_element(
            "css selector",
            '[data-action="delete"]',
        ).click()
        self.wait_for_task_absent(title)

    def priority(self, title: str) -> str:
        return self.wait_for_row(title).find_element(
            "css selector",
            ".priority",
        ).text

    def task_count(self) -> str:
        element = self.driver.find_element("id", "task-count")
        return (
            element.get_attribute("textContent")
            or ""
        ).strip()

    def api_request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict[str, object] | None = None,
    ) -> object:
        encoded_body = (
            json.dumps(body)
            if body is not None
            else None
        )

        result = self.driver.execute_async_script(
            """
            const path = arguments[0];
            const method = arguments[1];
            const encodedBody = arguments[2];
            const done = arguments[arguments.length - 1];

            const options = {
                method,
                headers: {
                    Accept: "application/json"
                }
            };

            if (encodedBody !== null) {
                options.headers["Content-Type"] =
                    "application/json";
                options.body = encodedBody;
            }

            fetch(path, options)
                .then(async response => {
                    const text = await response.text();
                    let payload = null;

                    if (text) {
                        try {
                            payload = JSON.parse(text);
                        } catch (_error) {
                            payload = text;
                        }
                    }

                    done({
                        ok: response.ok,
                        status: response.status,
                        payload
                    });
                })
                .catch(error => {
                    done({
                        ok: false,
                        status: 0,
                        error: String(error)
                    });
                });
            """,
            path,
            method,
            encoded_body,
        )

        if not isinstance(result, dict):
            raise AssertionError(
                f"Unexpected API result for {method} {path}: "
                f"{result!r}"
            )

        if not result.get("ok"):
            raise AssertionError(
                f"API request failed for {method} {path}: "
                f"status={result.get('status')}; "
                f"payload={result.get('payload')!r}; "
                f"error={result.get('error')!r}"
            )

        return result.get("payload")
