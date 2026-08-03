"""Stable browser interactions for the HardHead availability gate."""

from __future__ import annotations

from typing import Any


class ConnectionGate:
    """Drive and inspect the fail-closed connection recovery UI."""

    def __init__(
        self,
        driver: Any,
        *,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.timeout_seconds = timeout_seconds

    def _gate(self) -> Any:
        return self.driver.find_element(
            "id",
            "hardhead-availability",
        )

    def state(self) -> str:
        return (
            self._gate().get_attribute("data-connection-state")
            or ""
        )

    def reason(self) -> str:
        element = self.driver.find_element(
            "id",
            "hardhead-availability-reason",
        )
        return (
            element.get_attribute("textContent")
            or ""
        ).strip()

    def wait_for_state(self, expected_state: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: self.state() == expected_state
        )

    def wait_for_reason(self, expected_text: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: expected_text in self.reason()
        )

    def is_displayed(self) -> bool:
        return self._gate().is_displayed()

    def body_is_blocked(self) -> bool:
        classes = (
            self.driver.find_element(
                "tag name",
                "body",
            ).get_attribute("class")
            or ""
        ).split()
        return "connection-blocked" in classes

    def click_retry(self) -> None:
        self.driver.find_element(
            "id",
            "hardhead-availability-retry",
        ).click()

    def click_reload(self) -> None:
        self.driver.find_element(
            "id",
            "hardhead-availability-reload",
        ).click()
