"""Bounded, non-sensitive diagnostics for failed browser tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PATH_PATTERN = re.compile(
    r"(?:/home/[^\s]+|/data/[^\s]+|/tmp/[^\s]+)"
)
MAX_VISIBLE_TEXT = 4000
MAX_LOG_ENTRIES = 100


def sanitize_text(value: object, limit: int = MAX_VISIBLE_TEXT) -> str:
    text = str(value)
    text = PATH_PATTERN.sub("[private-path]", text)
    return text[:limit]


def create_test_directory(
    artifacts_root: Path,
    run_id: str,
    test_name: str,
) -> Path:
    safe_test_name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        test_name,
    ).strip("-") or "unnamed-test"
    directory = artifacts_root / run_id / safe_test_name
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def capture_failure(
    driver: Any,
    directory: Path,
    *,
    test_name: str,
    error: BaseException | None = None,
) -> None:
    metadata: dict[str, object] = {
        "test": sanitize_text(test_name, 256),
        "errorType": type(error).__name__ if error else "TestFailure",
        "error": sanitize_text(error or "Browser assertion failed."),
    }

    try:
        metadata["url"] = sanitize_text(driver.current_url, 1024)
    except BaseException:
        metadata["url"] = "unavailable"

    try:
        metadata["title"] = sanitize_text(driver.title, 512)
    except BaseException:
        metadata["title"] = "unavailable"

    try:
        body = driver.find_element("tag name", "body")
        metadata["visibleText"] = sanitize_text(body.text)
    except BaseException:
        metadata["visibleText"] = "unavailable"

    try:
        entries = driver.get_log("browser")[:MAX_LOG_ENTRIES]
        metadata["browserLog"] = [
            {
                "level": sanitize_text(entry.get("level", ""), 32),
                "message": sanitize_text(entry.get("message", ""), 1000),
            }
            for entry in entries
            if isinstance(entry, dict)
        ]
    except BaseException:
        metadata["browserLog"] = []

    try:
        driver.save_screenshot(str(directory / "failure.png"))
    except BaseException:
        metadata["screenshot"] = "unavailable"
    else:
        metadata["screenshot"] = "failure.png"

    (directory / "failure.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
