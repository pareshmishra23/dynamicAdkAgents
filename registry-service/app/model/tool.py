from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Tool(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tool_id: str
    name: str
    description: str = ""
    capability: str
    provider: str = ""
    enabled: bool = True
    config: dict[str, object] = {}
    created_at: str
    updated_at: str


class ToolCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tool_id: str
    name: str
    description: str = ""
    capability: str
    provider: str = ""
    enabled: bool = True
    config: dict[str, object] = {}


class ToolUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    description: str | None = None
    capability: str | None = None
    provider: str | None = None
    config: dict[str, object] | None = None
