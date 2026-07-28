import asyncio
import unittest

from httpx import ASGITransport, AsyncClient

from app.core.config import DATABASE_URL
from app.core.database import engine, initialize_database
from app.main import app
from app.models.base import Base


class ApiTestCase(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if "/tmp/" not in DATABASE_URL:
            raise RuntimeError(
                "Tests require a temporary SQLite database URL."
            )

        initialize_database()

    async def asyncSetUp(self) -> None:
        asyncio.get_running_loop().slow_callback_duration = 5
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()

    async def create_project(
        self,
        *,
        name: str = "Test Project",
        status: str = "planning",
    ) -> dict:
        response = await self.client.post(
            "/api/projects",
            json={
                "name": name,
                "status": status,
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()
