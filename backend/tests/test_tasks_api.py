from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.default_space import DEFAULT_SPACE_ID
from app.models.member import Member
from app.models.person import Person
from app.models.space import Space
from app.models.task import Task
from test_support import ApiTestCase


class TaskApiTests(ApiTestCase):
    def create_member_fixture(
        self,
        *,
        space_id: str = DEFAULT_SPACE_ID,
    ) -> str:
        with SessionLocal() as session:
            if space_id != DEFAULT_SPACE_ID:
                session.add(
                    Space(
                        id=space_id,
                        name=f"Space {space_id}",
                    )
                )
                session.flush()

            person = Person(
                display_name=f"Person {space_id}",
            )
            session.add(person)
            session.flush()

            member = Member(
                space_id=space_id,
                person_id=person.id,
                role="member",
            )
            session.add(member)
            session.flush()
            member_id = member.id
            session.commit()

        return member_id

    async def test_task_due_date_and_responsibility_are_space_scoped(
        self,
    ) -> None:
        responsible_member_id = self.create_member_fixture()
        cross_space_member_id = self.create_member_fixture(
            space_id="other-space",
        )

        created = await self.client.post(
            "/api/tasks",
            json={
                "title": "Scheduled work",
                "dueDate": "2026-08-20",
                "responsibleMemberId": responsible_member_id,
            },
        )
        self.assertEqual(created.status_code, 201)
        task = created.json()
        self.assertEqual(task["dueDate"], "2026-08-20")
        self.assertEqual(
            task["responsibleMemberId"],
            responsible_member_id,
        )

        rejected = await self.client.patch(
            f"/api/tasks/{task['id']}",
            json={
                "title": "Must not persist",
                "responsibleMemberId": cross_space_member_id,
            },
        )
        self.assertEqual(rejected.status_code, 404)

        unchanged = (
            await self.client.get(f"/api/tasks/{task['id']}")
        ).json()
        self.assertEqual(unchanged["title"], "Scheduled work")
        self.assertEqual(
            unchanged["responsibleMemberId"],
            responsible_member_id,
        )

        missing = await self.client.patch(
            f"/api/tasks/{task['id']}",
            json={"responsibleMemberId": "missing-member"},
        )
        self.assertEqual(missing.status_code, 404)

        cleared = await self.client.patch(
            f"/api/tasks/{task['id']}",
            json={
                "dueDate": None,
                "responsibleMemberId": None,
            },
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.json()["dueDate"])
        self.assertIsNone(cleared.json()["responsibleMemberId"])

    async def test_task_crud_completion_and_reopening(self) -> None:
        create_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Cut plywood",
                "priority": "high",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        task = create_response.json()
        self.assertNotIn("spaceId", task)

        with SessionLocal() as session:
            self.assertEqual(
                session.scalar(
                    select(Task.space_id).where(Task.id == task["id"])
                ),
                DEFAULT_SPACE_ID,
            )

        self.assertIsNone(task["projectId"])
        self.assertFalse(task["completed"])

        read_response = await self.client.get(
            f"/api/tasks/{task['id']}"
        )
        self.assertEqual(read_response.status_code, 200)

        update_response = await self.client.patch(
            f"/api/tasks/{task['id']}",
            json={
                "title": "Cut birch plywood",
                "priority": "medium",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["title"],
            "Cut birch plywood",
        )
        self.assertEqual(update_response.json()["priority"], "medium")

        complete_response = await self.client.post(
            f"/api/tasks/{task['id']}/complete"
        )
        self.assertTrue(complete_response.json()["completed"])

        reopen_response = await self.client.post(
            f"/api/tasks/{task['id']}/reopen"
        )
        self.assertFalse(reopen_response.json()["completed"])

        delete_response = await self.client.delete(
            f"/api/tasks/{task['id']}"
        )
        self.assertEqual(delete_response.status_code, 204)

        missing_response = await self.client.get(
            f"/api/tasks/{task['id']}"
        )
        self.assertEqual(missing_response.status_code, 404)

    async def test_task_can_associate_and_disassociate_project(self) -> None:
        project = await self.create_project(status="active")
        create_response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Project task",
                "priority": "low",
                "projectId": project["id"],
            },
        )

        self.assertEqual(create_response.status_code, 201)
        task = create_response.json()
        self.assertEqual(task["projectId"], project["id"])

        disassociate_response = await self.client.patch(
            f"/api/tasks/{task['id']}",
            json={"projectId": None},
        )
        self.assertEqual(disassociate_response.status_code, 200)
        self.assertIsNone(disassociate_response.json()["projectId"])

        associate_response = await self.client.patch(
            f"/api/tasks/{task['id']}",
            json={"projectId": project["id"]},
        )
        self.assertEqual(associate_response.status_code, 200)
        self.assertEqual(
            associate_response.json()["projectId"],
            project["id"],
        )

    async def test_missing_project_relationship_is_rejected(self) -> None:
        response = await self.client.post(
            "/api/tasks",
            json={
                "title": "Blocked relationship",
                "projectId": "missing-project",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Project not found.")

        space_response = await self.client.post(
            "/api/tasks",
            json={"title": "Client-scoped", "spaceId": "client-space"},
        )
        self.assertEqual(space_response.status_code, 422)

    async def test_deleting_project_unassigns_related_task(self) -> None:
        project = await self.create_project(status="active")
        related = (
            await self.client.post(
                "/api/tasks",
                json={
                    "title": "Related task",
                    "projectId": project["id"],
                },
            )
        ).json()
        unrelated = (
            await self.client.post(
                "/api/tasks",
                json={"title": "Unrelated task"},
            )
        ).json()

        deleted = await self.client.delete(
            f"/api/projects/{project['id']}"
        )
        self.assertEqual(deleted.status_code, 204)
        related_after = (
            await self.client.get(f"/api/tasks/{related['id']}")
        ).json()
        unrelated_after = (
            await self.client.get(f"/api/tasks/{unrelated['id']}")
        ).json()
        self.assertIsNone(related_after["projectId"])
        self.assertIsNone(unrelated_after["projectId"])

    async def test_task_validation_errors_are_clear(self) -> None:
        empty_title = await self.client.post(
            "/api/tasks",
            json={"title": "", "priority": "high"},
        )
        invalid_priority = await self.client.post(
            "/api/tasks",
            json={"title": "Invalid", "priority": "urgent"},
        )
        whitespace_title = await self.client.post(
            "/api/tasks",
            json={"title": "   ", "priority": "medium"},
        )
        empty_update = await self.client.patch(
            "/api/tasks/not-found",
            json={},
        )

        self.assertEqual(empty_title.status_code, 422)
        self.assertEqual(invalid_priority.status_code, 422)
        self.assertEqual(whitespace_title.status_code, 422)
        self.assertEqual(empty_update.status_code, 422)
