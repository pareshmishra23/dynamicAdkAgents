from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class McpServer(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    description: str = ""
    endpoint: str
    transport: str = "stdio"
    enabled: bool = True
    version: str = "1.0.0"
    created_at: str
    updated_at: str


class McpServerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    description: str = ""
    endpoint: str
    transport: str = "stdio"
    enabled: bool = True
    version: str = "1.0.0"


class McpServerUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    description: str | None = None
    endpoint: str | None = None
    transport: str | None = None
    version: str | None = None