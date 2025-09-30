"""Pydantic data models describing core Agent Lab contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentConfig(BaseModel):
    """Configuration metadata that defines how an agent should run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    model: str
    system_prompt: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    tools: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    """Telemetry record capturing a single model run and its outcomes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ts: datetime
    agent_name: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int
    cost_usd: float = 0.0
    experiment_id: str = ""
    task_label: str = ""
    run_notes: str = ""
    streaming: bool = True
    model_list_source: Literal["dynamic", "fallback"] = "fallback"
    tool_web_enabled: bool = False
    web_status: Literal["off", "ok", "blocked"] = "off"
    aborted: bool = False


class Session(BaseModel):
    """Persisted chat session pairing a config with conversation history."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    created_at: datetime
    agent_config: AgentConfig
    transcript: list[dict[str, Any]]
    model_id: str
    notes: str = ""


if __name__ == "__main__":
    sample_config = AgentConfig(
        name="Default Agent",
        model="openai/gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
    )

    sample_run = RunRecord(
        ts=datetime.utcnow(),
        agent_name=sample_config.name,
        model=sample_config.model,
        latency_ms=1200,
    )

    print("AgentConfig:")
    print(sample_config.model_dump())

    print("\nRunRecord:")
    print(sample_run.model_dump())
