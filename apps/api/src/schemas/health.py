from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.5.0"
    release: str = "Loki"
    environment: str


class ReadyResponse(BaseModel):
    status: str = "ready"
    database: str
    redis: str
