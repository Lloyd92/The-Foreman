"""Universal Work browser acceptance coverage."""

from __future__ import annotations

import os
import unittest

from foreman_e2e.application import ForemanApplication
from foreman_e2e.base import BrowserE2ETestCase
from foreman_e2e.projects import ProjectsPage
from foreman_e2e.tasks import TasksPage
from foreman_e2e.work import WorkPage


@unittest.skipUnless(
    os.environ.get("FOREMAN_E2E_RUNTIME") == "1",
    "Work acceptance requires the disposable deployment runner.",
)
class WorkOverviewTests(BrowserE2ETestCase):
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
        self.work = WorkPage(
            self.driver,
            timeout_seconds=self.config.timeout_seconds,
        )

    def test_normalized_work_overview_survives_reload(
        self,
    ) -> None:
        project_name = "E2E Universal Work Project"
        task_title = "E2E Universal Work Task"
        due_date = "2026-08-20"

        project = {
            "name": project_name,
            "type": "internal",
            "status": "active",
            "priority": "medium",
            "progress": 25,
            "startDate": "2026-08-10",
            "targetDate": "2026-08-30",
            "estimatedCost": 40,
            "description": "Universal Work browser acceptance.",
            "notes": "Disposable acceptance record.",
        }

        task_id = None
        project_id = None
        dependency_id = None

        try:
            self.app.open("tasks")
            self.tasks.create_task(
                task_title,
                "high",
                due_date=due_date,
            )
            self.assertEqual(
                self.tasks.due_date(task_title),
                f"Due {due_date}",
            )

            self.app.open("projects")
            self.projects.create_project(project)

            tasks = self.app.api_request("/api/tasks")
            projects = self.app.api_request("/api/projects")

            self.assertIsInstance(tasks, list)
            self.assertIsInstance(projects, list)

            matching_tasks = [
                item
                for item in tasks
                if item.get("title") == task_title
            ]
            matching_projects = [
                item
                for item in projects
                if item.get("name") == project_name
            ]

            self.assertEqual(len(matching_tasks), 1)
            self.assertEqual(len(matching_projects), 1)

            task_id = matching_tasks[0]["id"]
            project_id = matching_projects[0]["id"]

            associated = self.app.api_request(
                f"/api/tasks/{task_id}",
                method="PATCH",
                body={"projectId": project_id},
            )
            self.assertEqual(
                associated["projectId"],
                project_id,
            )

            dependency = self.app.api_request(
                "/api/work-dependencies",
                method="POST",
                body={
                    "dependentType": "task",
                    "dependentId": task_id,
                    "prerequisiteType": "project",
                    "prerequisiteId": project_id,
                },
            )
            self.assertIsInstance(dependency, dict)
            dependency_id = dependency["id"]

            expected_dependency = (
                f"{task_title} requires {project_name}"
            )

            self.app.open("work")

            self.assertEqual(
                self.work.summary(),
                {
                    "total": "2",
                    "openTasks": "1",
                    "projects": "1",
                    "dependencies": "1",
                },
            )

            self.assertEqual(
                self.work.item_values(task_title),
                {
                    "type": "TASK",
                    "state": "OPEN",
                    "priority": "High",
                    "progress": "0%",
                    "date": f"Due {due_date}",
                    "relationship": (
                        f"Project: {project_name}"
                    ),
                },
            )

            self.assertEqual(
                self.work.item_values(project_name),
                {
                    "type": "PROJECT",
                    "state": "ACTIVE",
                    "priority": "Medium",
                    "progress": "25%",
                    "date": "Target 2026-08-30",
                    "relationship": "Independent record",
                },
            )

            self.work.wait_for_dependency(
                expected_dependency
            )
            self.assertEqual(
                self.work.dependency_texts(),
                [expected_dependency],
            )

            # A fresh application startup proves the Overview is derived
            # again from backend-authoritative Work state.
            self.app.open("work")

            self.assertEqual(
                self.work.summary(),
                {
                    "total": "2",
                    "openTasks": "1",
                    "projects": "1",
                    "dependencies": "1",
                },
            )
            self.assertEqual(
                self.work.item_values(task_title)["date"],
                f"Due {due_date}",
            )
            self.assertEqual(
                self.work.item_values(task_title)[
                    "relationship"
                ],
                f"Project: {project_name}",
            )
            self.work.wait_for_dependency(
                expected_dependency
            )
        finally:
            if dependency_id is not None:
                self.app.api_request(
                    (
                        "/api/work-dependencies/"
                        f"{dependency_id}"
                    ),
                    method="DELETE",
                )

            if task_id is not None:
                self.app.api_request(
                    f"/api/tasks/{task_id}",
                    method="DELETE",
                )

            if project_id is not None:
                self.app.api_request(
                    f"/api/projects/{project_id}",
                    method="DELETE",
                )


if __name__ == "__main__":
    unittest.main()
