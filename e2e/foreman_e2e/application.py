"""Stable browser interactions for The Foreman application shell."""

from __future__ import annotations

import json
from typing import Any


PRIMARY_ROUTE_HEADINGS = {
    "today": ", Tyler.",
    "calendar": "Calendar",
    "work": "Work",
    "resources": "Resources",
    "money": "Money",
    "library": "Library",
    "settings": "Settings",
    "account": "Account",
}

SECONDARY_ROUTE_HEADINGS = {
    "tasks": "Tasks",
    "inventory": "Inventory",
    "projects": "Projects",
    "mealworms": "Mealworm Production",
    "budget": "Budget",
    "recovery": "Backup & Recovery",
}

ROUTE_HEADINGS = {
    **PRIMARY_ROUTE_HEADINGS,
    **SECONDARY_ROUTE_HEADINGS,
}

PARENT_NAV_ROUTES = {
    "tasks": "work",
    "projects": "work",
    "inventory": "resources",
    "mealworms": "resources",
    "budget": "money",
    "recovery": "settings",
}


class ForemanApplication:
    """Drive the application through stable public browser selectors."""

    def __init__(
        self,
        driver: Any,
        *,
        origin: str,
        timeout_seconds: float,
    ) -> None:
        self.driver = driver
        self.origin = origin.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def open(
        self,
        route: str = "today",
        *,
        expected_route: str | None = None,
    ) -> None:
        target = f"{self.origin}/#{route}"

        # A fragment-only Selenium navigation may reuse the existing
        # document. Leave the origin first so deep-link tests exercise
        # a genuine application startup for every route.
        self.driver.get("about:blank")
        self.driver.get(target)
        self.wait_for_document()
        self.wait_until_operational()
        self.wait_for_route(expected_route or route)

    def wait_for_document(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def wait_until_operational(self) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        wait = WebDriverWait(
            self.driver,
            self.timeout_seconds,
        )

        wait.until(
            lambda driver: (
                "connection-blocked"
                not in (
                    driver.find_element(
                        "tag name",
                        "body",
                    ).get_attribute("class")
                    or ""
                ).split()
            )
        )
        wait.until(
            lambda driver: driver.find_element(
                "id",
                "hardhead-availability",
            ).get_attribute("data-connection-state") == "online"
        )
        wait.until(
            lambda driver: not driver.find_element(
                "id",
                "hardhead-availability",
            ).is_displayed()
        )
        wait.until(
            lambda driver: driver.find_element(
                "id",
                "system-status",
            ).text == "System online"
        )
        wait.until(
            lambda driver: (
                driver.find_element(
                    "id",
                    "api-status",
                ).get_attribute("textContent")
                or ""
            ).strip() == "ONLINE"
        )

    def navigate(self, route: str) -> None:
        self.driver.find_element(
            "css selector",
            f'[data-route="{route}"]',
        ).click()
        self.wait_for_route(route)

    def wait_for_route(self, route: str) -> None:
        from selenium.webdriver.support.ui import WebDriverWait

        expected_navigation_route = PARENT_NAV_ROUTES.get(route, route)

        WebDriverWait(
            self.driver,
            self.timeout_seconds,
        ).until(
            lambda _driver: self.visible_routes() == [route]
            and self.active_route() == expected_navigation_route
        )

    def visible_routes(self) -> list[str]:
        return [
            page.get_attribute("data-page")
            for page in self.driver.find_elements(
                "css selector",
                "[data-page]",
            )
            if page.is_displayed()
        ]

    def active_route(self) -> str | None:
        active_links = self.driver.find_elements(
            "css selector",
            '[data-route].active[aria-current="page"]',
        )
        if len(active_links) != 1:
            return None
        return active_links[0].get_attribute("data-route")

    def heading(self, route: str) -> str:
        if route == "today":
            selector = "#greeting"
        else:
            selector = f'[data-page="{route}"] h2'

        return self.driver.find_element(
            "css selector",
            selector,
        ).text

    def text_by_id(self, element_id: str) -> str:
        element = self.driver.find_element(
            "id",
            element_id,
        )
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
        headers: dict[str, str] | None = None,
    ) -> object:
        """Issue a same-origin request from the disposable browser."""

        encoded_body = (
            json.dumps(body)
            if body is not None
            else None
        )
        encoded_headers = json.dumps(headers or {})

        result = self.driver.execute_async_script(
            """
            const path = arguments[0];
            const method = arguments[1];
            const encodedBody = arguments[2];
            const encodedHeaders = arguments[3];
            const done = arguments[arguments.length - 1];

            const options = {
                method,
                headers: {
                    Accept: "application/json",
                    ...JSON.parse(encodedHeaders)
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
            encoded_headers,
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
