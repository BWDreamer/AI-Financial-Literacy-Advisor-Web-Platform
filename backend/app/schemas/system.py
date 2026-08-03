from pydantic import BaseModel


class ApiIndexResponse(BaseModel):
    name: str
    version: str
    docs_url: str
    openapi_url: str
    health_url: str
    groups: dict[str, list[str]]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
