"""
Pydantic schemas for agent configuration validation.
"""

from typing import Dict, List
from pydantic import BaseModel, Field, field_validator, model_validator


class HandoffConfig(BaseModel):
    """Configuration for a single agent handoff."""

    to: str = Field(..., description="Target agent name")
    when: str = Field(..., description="When to make this transfer")

    class Config:
        frozen = True


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    name: str = Field(..., description="Unique agent identifier")
    model: str = Field(default="gpt-4o", description="LLM model")
    temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="Temperature")
    description: str = Field(..., description="Agent role and purpose")
    tools: List[str] = Field(default_factory=list, description="Tool names")
    handoffs: List[HandoffConfig] = Field(default_factory=list, description="Handoff targets")
    prompt_file: str | None = Field(None, description="Prompt YAML file")
    tags: List[str] = Field(default_factory=list, description="Tags for tracking")

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"Temperature must be 0.0-2.0, got {v}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.islower() or " " in v:
            raise ValueError(f"Agent name must be lowercase with underscores: '{v}'")
        return v

    @model_validator(mode="after")
    def set_defaults(self) -> "AgentConfig":
        if self.prompt_file is None:
            self.prompt_file = f"{self.name}.yaml"
        if not self.tags:
            self.tags = [self.name]
        return self

    class Config:
        frozen = True


class AgentSystemConfig(BaseModel):
    """Complete system configuration containing all agents."""

    agents: Dict[str, AgentConfig] = Field(..., description="All agent configs")
    default_agent: str = Field(default="eic", description="Default starting agent")

    @model_validator(mode="after")
    def validate_system(self) -> "AgentSystemConfig":
        agent_names = set(self.agents.keys())

        # Validate default agent exists
        if self.default_agent not in agent_names:
            raise ValueError(f"Default agent '{self.default_agent}' not in agents: {agent_names}")

        # Validate all handoff targets exist
        for agent_name, agent_config in self.agents.items():
            for handoff in agent_config.handoffs:
                if handoff.to not in agent_names:
                    raise ValueError(f"Agent '{agent_name}' handoff to unknown '{handoff.to}'")

        return self

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent."""
        if agent_name not in self.agents:
            raise KeyError(f"Agent '{agent_name}' not found")
        return self.agents[agent_name]

    def get_handoff_targets(self, agent_name: str) -> List[HandoffConfig]:
        """Get handoff targets for an agent."""
        return self.get_agent_config(agent_name).handoffs

    class Config:
        frozen = True
