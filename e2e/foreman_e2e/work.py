"""Stable browser interactions for the normalized Work overview."""

from __future__ import annotations

from typing import Any


class WorkPage:
    """Inspect backend-authoritative Work through public UI selectors."""

    def __init__(
        self,
        driver: Any,
        *,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.timeout_seconds = timeout_seconds

    def _text_by_id(self, element_id: str) -> str:
        element = self.driver.find_element("id", element_id)
        return (
            element.get_attribute("textContent")
            or ""
        ).strip()

    def wait_for_loaded(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: (
                self._text_by_id("work-page-message") == ""
                and not self.driver.find_element(
                    "id",
                    "retry-work",
                ).is_displayed()
            )
        )

    def summary(self) -> dict[str, str]:
        self.wait_for_loaded()
        return {
            "total": self._text_by_id("work-total-count"),
            "openTasks": self._text_by_id(
                "work-open-task-count"
            ),
            "projects": self._text_by_id(
                "work-project-count"
            ),
            "dependencies": self._text_by_id(
                "work-dependency-count"
            ),
        }

    def find_item(self, title: str) -> Any | None:
        for card in self.driver.find_elements(
            "css selector",
            "#work-overview-items .work-overview-item",
        ):
            titles = card.find_elements(
                "css selector",
                ".work-item-title",
            )
            if titles and titles[0].text == title:
                return card

        return None

    def wait_for_item(self, title: str) -> Any:
        from selenium.common.exceptions import (
            StaleElementReferenceException,
        )
        from selenium.webdriver.support.ui import WebDriverWait

        def locate(_driver: Any) -> Any | bool:
            try:
                return self.find_item(title) or False
            except StaleElementReferenceException:
                return False

        return WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(locate)

    def item_values(self, title: str) -> dict[str, str]:
        card = self.wait_for_item(title)

        def text(selector: str) -> str:
            return card.find_element(
                "css selector",
                selector,
            ).text

        return {
            "type": text(".work-item-type"),
            "state": text(".work-item-state"),
            "priority": text(".work-item-priority"),
            "progress": text(".work-item-progress"),
            "date": text(".work-item-date"),
            "relationship": text(
                ".work-item-relationship"
            ),
        }

    def dependency_texts(self) -> list[str]:
        self.wait_for_loaded()
        return [
            row.text
            for row in self.driver.find_elements(
                "css selector",
                "#work-overview-dependencies "
                ".work-dependency-row",
            )
        ]

    def wait_for_dependency(self, expected: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: expected in self.dependency_texts()
        )
