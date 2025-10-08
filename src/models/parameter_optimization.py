"""Pydantic data models for AI Parameter Optimization feature."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Literal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class UseCaseType(str, Enum):
    """Enumeration of supported use case types for parameter optimization."""

    CREATIVE_WRITING = "creative_writing"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    CONVERSATION = "conversation"
    REASONING = "reasoning"
    DEBUGGING = "debugging"
    TRANSLATION = "translation"
    OTHER = "other"


class UseCaseDetectionResult(BaseModel):
    """Result of use case detection analysis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    detected_use_case: UseCaseType = Field(..., description="Primary detected use case")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in detection (0.0-1.0)")
    secondary_use_cases: List[UseCaseType] = Field(default_factory=list, description="Secondary use cases detected")
    keywords_matched: List[str] = Field(default_factory=list, description="Keywords that triggered detection")
    context_hints: Dict[str, float] = Field(default_factory=dict, description="Context hints with confidence scores")


class ParameterRecommendation(BaseModel):
    """Recommended parameter values for a specific use case."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    temperature: float = Field(..., ge=0.0, le=2.0, description="Recommended temperature setting")
    top_p: float = Field(..., ge=0.0, le=1.0, description="Recommended top_p setting")
    max_tokens: int = Field(..., gt=0, description="Recommended max tokens per request")
    reasoning: str = Field(..., description="Explanation for these parameter recommendations")


class OptimizationContext(BaseModel):
    """Context information for parameter optimization."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_id: str = Field(..., description="Model identifier")
    use_case: UseCaseType = Field(..., description="Detected use case")
    user_input_length: int = Field(default=0, description="Length of user input in characters")
    conversation_history_length: int = Field(default=0, description="Number of previous messages")
    task_complexity_hint: Optional[str] = Field(None, description="User-provided complexity hint")
    time_pressure: Optional[Literal["low", "medium", "high"]] = Field(None, description="Time pressure indicator")


class HistoricalPattern(BaseModel):
    """Historical success pattern for parameter combinations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    use_case: UseCaseType = Field(..., description="Use case this pattern applies to")
    model_id: str = Field(..., description="Model this pattern was successful with")
    temperature: float = Field(..., description="Temperature used")
    top_p: float = Field(..., description="Top-p used")
    max_tokens: int = Field(..., description="Max tokens used")
    success_score: float = Field(..., ge=0.0, le=1.0, description="Success score (0.0-1.0)")
    usage_count: int = Field(default=1, description="Number of times this pattern was used")
    last_used: datetime = Field(default_factory=lambda: datetime.now(), description="Last time this pattern was used")
    avg_latency_ms: float = Field(default=0.0, description="Average latency in milliseconds")
    avg_cost_usd: float = Field(default=0.0, description="Average cost per request")


class ParameterOptimizationRequest(BaseModel):
    """Request for parameter optimization."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_id: str = Field(..., description="Target model identifier")
    user_description: str = Field(..., description="User's description of their task/use case")
    context: OptimizationContext = Field(..., description="Additional context for optimization")
    include_historical_learning: bool = Field(default=True, description="Whether to incorporate historical data")


class ParameterOptimizationResponse(BaseModel):
    """Response containing optimized parameters."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    recommended_parameters: ParameterRecommendation = Field(..., description="Recommended parameter settings")
    use_case_detection: UseCaseDetectionResult = Field(..., description="Details of use case detection")
    historical_insights: Optional[Dict[str, float]] = Field(None, description="Insights from historical data")
    optimization_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in optimization")
    processing_time_ms: float = Field(..., description="Time taken to generate recommendations")


class SmartDefaultsRequest(BaseModel):
    """Request for smart default parameters."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_id: str = Field(..., description="Target model identifier")
    user_context: Optional[str] = Field(None, description="User's current context or recent activity")


class SmartDefaultsResponse(BaseModel):
    """Response containing smart default parameters."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    default_parameters: ParameterRecommendation = Field(..., description="Smart default parameter settings")
    reasoning: str = Field(..., description="Explanation for these defaults")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in these defaults")


if __name__ == "__main__":
    # Example usage
    sample_detection = UseCaseDetectionResult(
        detected_use_case=UseCaseType.CREATIVE_WRITING,
        confidence_score=0.92,
        secondary_use_cases=[UseCaseType.ANALYSIS],
        keywords_matched=["creative", "story", "writing"],
        context_hints={"creativity": 0.95, "structure": 0.78}
    )

    sample_recommendation = ParameterRecommendation(
        temperature=0.9,
        top_p=0.95,
        max_tokens=2000,
        reasoning="High temperature and top_p encourage creative output, extended max_tokens for longer content"
    )

    sample_context = OptimizationContext(
        model_id="openai/gpt-4o",
        use_case=UseCaseType.CREATIVE_WRITING,
        user_input_length=150,
        conversation_history_length=5,
        task_complexity_hint="complex",
        time_pressure="low"
    )

    sample_request = ParameterOptimizationRequest(
        model_id="openai/gpt-4o",
        user_description="I want to write a creative short story about AI",
        context=sample_context
    )

    sample_response = ParameterOptimizationResponse(
        recommended_parameters=sample_recommendation,
        use_case_detection=sample_detection,
        historical_insights={"temperature": 0.85, "success_rate": 0.78},
        optimization_confidence=0.91,
        processing_time_ms=45.2
    )

    print("UseCaseDetectionResult:")
    print(sample_detection.model_dump())

    print("\nParameterRecommendation:")
    print(sample_recommendation.model_dump())

    print("\nParameterOptimizationResponse:")
    print(sample_response.model_dump())