from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentPolicy(BaseModel):
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int | None = None
    timeout_seconds: int = Field(default=60, gt=0)
    max_tool_calls: int = Field(default=20, gt=0)
    max_retries: int = Field(default=2, ge=0)
    max_iterations: int = Field(default=3, gt=0)


class OutputContract(BaseModel):
    type: str = "object"
    required: list[str] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)


class Agent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    description: str = ""
    capability: str
    model: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    policy: AgentPolicy = Field(default_factory=AgentPolicy)
    output_contract: OutputContract | None = None
    requires_human_approval: bool = False
    created_at: str
    updated_at: str


class AgentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    name: str
    description: str = ""
    capability: str = ""
    capabilities: list[str] | None = None
    model: str = "default-model"
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    policy: AgentPolicy | None = None
    output_contract: OutputContract | None = None
    requires_human_approval: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_capabilities(cls, data: Any) -> Any:
        if isinstance(data, dict):
            caps = data.get("capabilities")
            if caps and not data.get("capability"):
                if isinstance(caps, (list, tuple)):
                    data["capability"] = ", ".join(str(c) for c in caps)
                else:
                    data["capability"] = str(caps)
            elif data.get("capability") and not caps:
                data["capabilities"] = [c.strip() for c in str(data["capability"]).split(",") if c.strip()]
        return data


class AgentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    description: str | None = None
    capability: str | None = None
    model: str | None = None
    config: dict[str, Any] | None = None
    policy: AgentPolicy | None = None
    output_contract: OutputContract | None = None
    requires_human_approval: bool | None = None