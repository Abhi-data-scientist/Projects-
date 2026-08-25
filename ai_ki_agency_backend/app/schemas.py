from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AgentName = Literal[
    "requirement",
    "architecture",
    "tools",
    "cost",
    "preview",
    "coding",
    "bug_report",
    "bug_fix",
    "package",
]


class PipelineRequest(BaseModel):
    """The single API request shape for starting sessions and running agents."""

    action: Literal["start", "run_agent", "download"]
    query: str | None = Field(
        default=None,
        min_length=3,
        description="Required with action='start'.",
    )
    tech_hint: str | None = Field(
        default=None,
        description="Optional hint about existing stack, e.g. 'plain HTML/CSS/JS site' or 'React app'",
    )
    session_id: str | None = Field(default=None, description="Required with action='run_agent'.")
    agent: AgentName | None = Field(default=None, description="Required with action='run_agent'.")
    artifact: str | None = Field(default=None, description="Required with action='download'.")

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "start" and not self.query:
            raise ValueError("query is required when action is 'start'")
        if self.action == "run_agent" and (not self.session_id or not self.agent):
            raise ValueError("session_id and agent are required when action is 'run_agent'")
        if self.action == "download" and (not self.session_id or not self.artifact):
            raise ValueError("session_id and artifact are required when action is 'download'")
        return self


class AgentResult(BaseModel):
    agent: AgentName
    status: Literal["success", "error"]
    output: Any
    error: str | None = None


class SessionState(BaseModel):
    session_id: str
    query: str
    tech_hint: str | None = None
    results: dict[str, AgentResult] = Field(default_factory=dict)
    completed_stage: str | None = None


class PipelineResponse(BaseModel):
    message: str
    session: SessionState
    agent_result: AgentResult | None = None
