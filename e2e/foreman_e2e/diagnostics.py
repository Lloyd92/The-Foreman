"""Bounded, non-sensitive diagnostics for failed browser tests."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


MAX_BROWSER_LOG_ENTRIES = 100
MAX_DRIVER_LOG_BYTES = 1_000_000
MAX_SCREENSHOT_BYTES = 5_000_000
SAFE_ROUTE = re.compile(r"^#[A-Za-z0-9_-]{0,64}$")
SAFE_IDENTIFIER = re.compile(r"[^A-Za-z0-9._-]+")
SAFE_LOG_LEVELS = (
    "TRACE",
    "DEBUG",
    "INFO",
    "WARN",
    "WARNING",
    "ERROR",
    "FATAL",
    "SEVERE",
)
SAFE_READY_STATES = {
    "loading",
    "interactive",
    "complete",
    "unknown",
}
SAFE_CONNECTION_STATES = {
    "checking",
    "online",
    "unavailable",
    "restored",
    "unknown",
}
SAFE_BODY_FLAGS = {
    "connection-blocked",
    "dialog-open",
}


def sanitize_identifier(value: object, limit: int = 256) -> str:
    text = SAFE_IDENTIFIER.sub("-", str(value)).strip("-")
    return (text or "unavailable")[:limit]


def safe_current_location(value: object) -> str:
    try:
        parsed = urlsplit(str(value))
    except ValueError:
        return "unavailable"

    if parsed.scheme not in {"http", "https"}:
        return "unavailable"

    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return "unavailable"

    route = parsed.fragment
    fragment = f"#{route}" if route else ""

    if fragment and not SAFE_ROUTE.fullmatch(fragment):
        fragment = "#unknown"

    return f"{parsed.path or '/'}{fragment}"


def create_test_directory(
    artifacts_root: Path,
    run_id: str,
    test_name: str,
) -> Path:
    safe_test_name = sanitize_identifier(test_name)
    directory = artifacts_root / run_id / safe_test_name
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _safe_page_state(driver: Any) -> dict[str, object]:
    script = """
        const body = document.body;
        const gate = document.getElementById("hardhead-availability");
        const visible = element => {
            if (!element) {
                return false;
            }
            const style = window.getComputedStyle(element);
            return (
                style.display !== "none" &&
                style.visibility !== "hidden" &&
                element.getClientRects().length > 0
            );
        };
        return {
            route: window.location.hash || "",
            readyState: document.readyState || "unknown",
            connectionState:
                gate?.getAttribute("data-connection-state") || "unknown",
            bodyFlags: body
                ? [...body.classList].filter(value => (
                    value === "connection-blocked" ||
                    value === "dialog-open"
                ))
                : [],
            visiblePageCount: [
                ...document.querySelectorAll("[data-page]")
            ].filter(visible).length,
            visibleDialogCount: [
                ...document.querySelectorAll(
                    '[role="dialog"], dialog, [id$="-dialog-backdrop"]'
                )
            ].filter(visible).length,
            dirtyFormCount: [
                ...document.querySelectorAll("form")
            ].filter(form => form.matches("[data-dirty='true']")).length,
            updateNoticeVisible: visible(
                document.querySelector(".pwa-update-notice")
            )
        };
    """

    try:
        raw = driver.execute_script(script)
    except BaseException:
        return {
            "route": "unavailable",
            "readyState": "unknown",
            "connectionState": "unknown",
            "bodyFlags": [],
            "visiblePageCount": 0,
            "visibleDialogCount": 0,
            "dirtyFormCount": 0,
            "updateNoticeVisible": False,
        }

    if not isinstance(raw, dict):
        raw = {}

    route = raw.get("route", "")
    route = (
        route
        if isinstance(route, str) and SAFE_ROUTE.fullmatch(route)
        else "#unknown"
    )

    ready_state = raw.get("readyState", "unknown")
    if ready_state not in SAFE_READY_STATES:
        ready_state = "unknown"

    connection_state = raw.get("connectionState", "unknown")
    if connection_state not in SAFE_CONNECTION_STATES:
        connection_state = "unknown"

    body_flags = raw.get("bodyFlags", [])
    if not isinstance(body_flags, list):
        body_flags = []

    def bounded_count(name: str) -> int:
        value = raw.get(name, 0)
        return min(value, 100) if isinstance(value, int) and value >= 0 else 0

    return {
        "route": route,
        "readyState": ready_state,
        "connectionState": connection_state,
        "bodyFlags": sorted(
            value
            for value in body_flags
            if value in SAFE_BODY_FLAGS
        ),
        "visiblePageCount": bounded_count("visiblePageCount"),
        "visibleDialogCount": bounded_count("visibleDialogCount"),
        "dirtyFormCount": bounded_count("dirtyFormCount"),
        "updateNoticeVisible": raw.get("updateNoticeVisible") is True,
    }


def _browser_log_summary(driver: Any) -> dict[str, object]:
    counts = {level: 0 for level in SAFE_LOG_LEVELS}

    try:
        entries = driver.get_log("browser")
    except BaseException:
        return {
            "available": False,
            "capturedEntries": 0,
            "truncated": False,
            "levels": counts,
        }

    if not isinstance(entries, list):
        entries = []

    captured = entries[:MAX_BROWSER_LOG_ENTRIES]

    for entry in captured:
        if not isinstance(entry, dict):
            continue
        level = str(entry.get("level", "")).upper()
        if level in counts:
            counts[level] += 1

    return {
        "available": True,
        "capturedEntries": len(captured),
        "truncated": len(entries) > MAX_BROWSER_LOG_ENTRIES,
        "levels": counts,
    }


def _redacted_screenshot(
    driver: Any,
    directory: Path,
    page_state: dict[str, object],
) -> str:
    screenshot_path = directory / "failure.png"
    overlay_id = "foreman-e2e-diagnostic-overlay"
    style_id = "foreman-e2e-diagnostic-style"
    safe_lines = [
        "Foreman E2E Failure Diagnostic",
        f"Route: {page_state['route']}",
        f"Document: {page_state['readyState']}",
        f"Connection: {page_state['connectionState']}",
        f"Visible pages: {page_state['visiblePageCount']}",
        f"Visible dialogs: {page_state['visibleDialogCount']}",
        f"Dirty forms: {page_state['dirtyFormCount']}",
        (
            "Update notice: visible"
            if page_state["updateNoticeVisible"]
            else "Update notice: hidden"
        ),
    ]

    install_script = """
        const overlayId = arguments[0];
        const styleId = arguments[1];
        const lines = arguments[2];

        document.getElementById(overlayId)?.remove();
        document.getElementById(styleId)?.remove();

        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = `
            body > *:not(#${overlayId}) {
                visibility: hidden !important;
            }
            #${overlayId},
            #${overlayId} * {
                visibility: visible !important;
            }
            #${overlayId} {
                position: fixed;
                inset: 0;
                z-index: 2147483647;
                box-sizing: border-box;
                padding: 48px;
                background: #15171a;
                color: #f2f2f2;
                font: 20px/1.6 sans-serif;
                white-space: pre-line;
            }
        `;

        const overlay = document.createElement("div");
        overlay.id = overlayId;
        overlay.setAttribute("role", "presentation");
        overlay.textContent = lines.join("\\n");

        document.head.appendChild(style);
        document.body.appendChild(overlay);
    """

    cleanup_script = """
        document.getElementById(arguments[0])?.remove();
        document.getElementById(arguments[1])?.remove();
    """

    try:
        driver.execute_script(
            install_script,
            overlay_id,
            style_id,
            safe_lines,
        )
        driver.save_screenshot(str(screenshot_path))
    except BaseException:
        screenshot_path.unlink(missing_ok=True)
        return "unavailable"
    finally:
        try:
            driver.execute_script(
                cleanup_script,
                overlay_id,
                style_id,
            )
        except BaseException:
            pass

    try:
        screenshot_size = screenshot_path.stat().st_size
    except OSError:
        return "unavailable"

    if screenshot_size > MAX_SCREENSHOT_BYTES:
        screenshot_path.unlink(missing_ok=True)
        return "unavailable"

    return screenshot_path.name


def capture_failure(
    driver: Any,
    directory: Path,
    *,
    test_name: str,
    error: BaseException | None = None,
) -> None:
    page_state = _safe_page_state(driver)

    metadata: dict[str, object] = {
        "schemaVersion": 1,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "test": sanitize_identifier(test_name),
        "failureType": (
            sanitize_identifier(type(error).__name__, 64)
            if error
            else "TestFailure"
        ),
        "location": safe_current_location(
            getattr(driver, "current_url", "")
        ),
        "pageState": page_state,
        "browserLogSummary": _browser_log_summary(driver),
    }

    metadata["screenshot"] = _redacted_screenshot(
        driver,
        directory,
        page_state,
    )

    (directory / "failure.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def finalize_driver_log(directory: Path) -> None:
    log_path = directory / "geckodriver.log"

    try:
        source_size = log_path.stat().st_size
        with log_path.open("r", encoding="utf-8", errors="replace") as stream:
            bounded_text = stream.read(MAX_DRIVER_LOG_BYTES)
    except OSError:
        bounded_text = ""
        source_size = 0

    level_counts = {level: 0 for level in SAFE_LOG_LEVELS}

    for line in bounded_text.splitlines():
        upper = line.upper()
        for level in SAFE_LOG_LEVELS:
            if re.search(rf"\b{re.escape(level)}\b", upper):
                level_counts[level] += 1
                break

    summary = {
        "schemaVersion": 1,
        "rawContentRetained": False,
        "sourceBytes": source_size,
        "capturedBytes": len(bounded_text.encode("utf-8")),
        "truncated": source_size > MAX_DRIVER_LOG_BYTES,
        "lineCount": len(bounded_text.splitlines()),
        "levels": level_counts,
    }

    log_path.write_text(
        "Foreman E2E geckodriver summary\n" +
        json.dumps(summary, indent=2, sort_keys=True) +
        "\n",
        encoding="utf-8",
        newline="\n",
    )
