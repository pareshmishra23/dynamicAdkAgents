from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Agent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    description: str = ""
    capability: str
    model: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class AgentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    description: str = ""
    capability: str
    model: str = "default-model"
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    description: str | None = None
    capability: str | None = None
    model: str | None = None
    config: dict[str, Any] | None = None