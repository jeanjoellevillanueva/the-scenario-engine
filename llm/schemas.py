from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class ObjectiveProgress(BaseModel):
    """Progress on a single learning objective."""

    status: Literal['not_yet', 'partial', 'met']
    evidence: str | None = None


class AssessmentResult(BaseModel):
    """Structured assessment returned by the LLM alongside each message."""

    objectives_addressed: list[str] = Field(
        default_factory=list,
        description='List of objective IDs addressed in this turn',
    )
    objective_progress: dict[str, ObjectiveProgress] = Field(
        default_factory=dict,
        description='Progress on each learning objective',
    )
    overall_score: int = Field(
        default=0,
        ge=0,
        le=5,
        description='Overall performance score (0-5)',
    )
    scenario_state: str = Field(
        default='unknown',
        description='Current phase of the scenario',
    )
    flags: list[str] = Field(
        default_factory=list,
        description='Behavioral flags detected',
    )


class LLMResponse(BaseModel):
    """Complete response from the LLM including message and assessment."""

    message: str = Field(
        description='The conversational reply from the character',
    )
    assessment: AssessmentResult = Field(
        default_factory=AssessmentResult,
        description='Structured assessment of learner progress',
    )


class LLMClientResponse(BaseModel):
    """Raw response metadata from the LLM client."""

    content: str = Field(description='Raw response content from the API')
    input_tokens: int = Field(default=0, description='Tokens in the request')
    output_tokens: int = Field(default=0, description='Tokens in the response')
    model: str = Field(default='', description='Model used for completion')
    latency_ms: float = Field(default=0.0, description='Request latency in milliseconds')
