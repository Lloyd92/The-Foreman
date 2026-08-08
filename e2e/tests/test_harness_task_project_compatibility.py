"""Task and Project browser compatibility coverage."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.projects import ProjectsPage
from foreman_e2e.tasks import TasksPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Task compatibility requires the disposable deployment runner.",
)
class TaskProjectCompatibilityTests(BrowserE2ETestCase):
    def setUp(self) -> None:
        super().setUp()
        self.app = ForemanApplication(
            self.driver,
            origin=self.config.origin,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.projects = ProjectsPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )
        self.tasks = TasksPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )

    def test_project_deletion_preserves_related_task(self) -> None:
        project_name = "E2E Task Compatibility Project"
        task_title = "E2E Preserve Related Task"

        project = {
            "name": project_name,
            "type": "internal",
            "status": "active",
            "priority": "medium",
            "progress": 10,
            "startDate": "2026-08-02",
            "targetDate": "2026-08-30",
            "estimatedCost": 25,
            "description": "Project associated with an E2E Task.",
            "notes": "Compatibility coverage.",
        }

        self.app.open("projects")
        self.projects.create_project(project)

        self.app.open("tasks")
        self.tasks.create_task(task_title, "high")

        self.assertEqual(
            self.tasks.priority(task_title),
            "HIGH",
        )
        self.assertFalse(
            self.tasks.is_completed(task_title),
        )

        self.tasks.toggle_task(
            task_title,
            expected_completed=True,
        )
        self.assertTrue(
            self.tasks.is_completed(task_title),
        )

        # Reload proves completion came back from HardHead.
        self.app.open("tasks")
        self.assertTrue(
            self.tasks.is_completed(task_title),
        )

        self.tasks.toggle_task(
            task_title,
            expected_completed=False,
        )
        self.assertFalse(
            self.tasks.is_completed(task_title),
        )

        project_records = self.tasks.api_request(
            "/api/projects"
        )
        task_records = self.tasks.api_request(
            "/api/tasks"
        )

        self.assertIsInstance(project_records, list)
        self.assertIsInstance(task_records, list)

        matching_projects = [
            item
            for item in project_records
            if item.get("name") == project_name
        ]
        matching_tasks = [
            item
            for item in task_records
            if item.get("title") == task_title
        ]

        self.assertEqual(len(matching_projects), 1)
        self.assertEqual(len(matching_tasks), 1)

        project_id = matching_projects[0]["id"]
        task_id = matching_tasks[0]["id"]

        associated_task = self.tasks.api_request(
            f"/api/tasks/{task_id}",
            method="PATCH",
            body={"projectId": project_id},
        )

        self.assertEqual(
            associated_task["projectId"],
            project_id,
        )

        persisted_association = self.tasks.api_request(
            f"/api/tasks/{task_id}"
        )
        self.assertEqual(
            persisted_association["projectId"],
            project_id,
        )

        # Delete through the visible Project UI. HardHead must preserve
        # the Task and clear only the Project relationship.
        self.app.open("projects")
        self.projects.delete_project(project_name)

        task_after_project_deletion = self.tasks.api_request(
            f"/api/tasks/{task_id}"
        )

        self.assertEqual(
            task_after_project_deletion["title"],
            task_title,
        )
        self.assertIsNone(
            task_after_project_deletion["projectId"],
        )
        self.assertFalse(
            task_after_project_deletion["completed"],
        )

        self.app.open("tasks")
        self.tasks.wait_for_row(task_title)
        self.assertFalse(
            self.tasks.is_completed(task_title),
        )

        self.tasks.delete_task(task_title)
        self.tasks.wait_for_task_absent(task_title)

        remaining_tasks = self.tasks.api_request("/api/tasks")
        self.assertFalse(
            any(
                task.get("id") == task_id
                for task in remaining_tasks
            )
        )

        self.app.open("projects")
        self.assertIsNone(
            self.projects.find_card(project_name),
        )


if __name__ == "__main__":
    unittest.main()
