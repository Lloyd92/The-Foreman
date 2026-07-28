from typing import Literal

from pydantic import BaseModel


class StatusResponse(BaseModel):
    application: str
    company: str
    status: Literal["online"]
    version: str


class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    database: Literal["online", "offline"]
    reason: str
