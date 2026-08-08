"""Tests for explicit clean-deployment acceptance."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from foreman_e2e.acceptance import (
    CleanDeploymentAcceptanceError,
    verify_clean_collections,
    verify_project_cleanup,
)
from foreman_e2e.config import REPOSITORY_ROOT


PROJECT = "foreman-e2e-20260803t030000z-12345"


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class CleanCollectionTests(unittest.TestCase):
    def test_accepts_four_empty_collections(self):
        calls = []

        def opener(request, timeout):
            calls.append((request.full_url, timeout))
            return FakeResponse([])

        counts = verify_clean_collections(
            "http://127.0.0.1:38123",
            opener=opener,
        )

        self.assertEqual(
            counts,
            {
                "/api/inventory": 0,
                "/api/projects": 0,
                "/api/tasks": 0,
                "/api/work-dependencies": 0,
            },
        )
        self.assertEqual(len(calls), 4)
        self.assertTrue(
            all(url.startswith("http://127.0.0.1:38123/api/")
                for url, _timeout in calls)
        )

    def test_rejects_nonempty_or_malformed_collection(self):
        for payload in ([{"id": "record"}], {"items": []}):
            with self.subTest(payload=payload):
                with self.assertRaises(
                    CleanDeploymentAcceptanceError
                ):
                    verify_clean_collections(
                        "http://127.0.0.1:38123",
                        opener=lambda *_args, **_kwargs:
                            FakeResponse(payload),
                    )

    def test_rejects_non_success_response(self):
        with self.assertRaises(CleanDeploymentAcceptanceError):
            verify_clean_collections(
                "http://127.0.0.1:38123",
                opener=lambda *_args, **_kwargs:
                    FakeResponse([], status=500),
            )


class CleanupVerificationTests(unittest.TestCase):
    def test_accepts_zero_project_resources(self):
        commands = []

        def runner(command, **_kwargs):
            commands.append(command)
            return SimpleNamespace(
                returncode=0,
                stdout="",
                stderr="",
            )

        counts = verify_project_cleanup(
            PROJECT,
            runner=runner,
        )

        self.assertEqual(
            counts,
            {
                "containers": 0,
                "networks": 0,
                "images": 0,
            },
        )
        self.assertEqual(len(commands), 3)
        self.assertTrue(
            all(PROJECT in " ".join(command)
                for command in commands)
        )

    def test_rejects_remaining_project_resource(self):
        def runner(command, **_kwargs):
            output = (
                "abc123\n"
                if command[1:3] == ["ps", "-aq"]
                else ""
            )
            return SimpleNamespace(
                returncode=0,
                stdout=output,
                stderr="",
            )

        with self.assertRaises(CleanDeploymentAcceptanceError):
            verify_project_cleanup(PROJECT, runner=runner)

    def test_rejects_unsafe_project_name(self):
        with self.assertRaises(CleanDeploymentAcceptanceError):
            verify_project_cleanup("foreman")


class RunnerAcceptanceContractTests(unittest.TestCase):
    def test_runner_orders_acceptance_and_cleanup(self):
        runner = (
            Path(REPOSITORY_ROOT)
            / "scripts"
            / "run_browser_e2e.sh"
        ).read_text(encoding="utf-8")

        health = runner.index("-m foreman_e2e.wait_for_health")
        clean_state = runner.index(
            "-m foreman_e2e.acceptance clean-state"
        )
        browser_tests = runner.index("-m unittest discover")
        explicit_down = runner.rindex(
            '"${compose[@]}" down'
        )
        cleanup_check = runner.index(
            "-m foreman_e2e.acceptance cleanup"
        )

        self.assertLess(health, clean_state)
        self.assertLess(clean_state, browser_tests)
        self.assertLess(browser_tests, explicit_down)
        self.assertLess(explicit_down, cleanup_check)
        self.assertIn("trap - EXIT INT TERM", runner)
        self.assertIn(
            "Clean deployment browser acceptance passed.",
            runner,
        )


if __name__ == "__main__":
    unittest.main()
