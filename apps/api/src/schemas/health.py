from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str


class ReadyResponse(BaseModel):
    status: str = "ready"
    database: str
    redis: str
