"""Pydantic data models for AI Model Matchmaker feature."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UseCaseInput(BaseModel):
    """Input model for user use case analysis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    description: str = Field(
        ..., description="Natural language description of the use case"
    )
    max_cost: Optional[float] = Field(
        None, description="Maximum acceptable cost per 1K tokens"
    )
    min_speed: Optional[float] = Field(
        None, description="Minimum acceptable speed (tokens/second)"
    )
    context_length_required: Optional[int] = Field(
        None, description="Minimum context window required"
    )


class SuggestedConfig(BaseModel):
    """Suggested configuration parameters for a model."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    temperature: float = Field(
        ..., ge=0.0, le=2.0, description="Suggested temperature setting"
    )
    top_p: float = Field(..., ge=0.0, le=1.0, description="Suggested top_p setting")
    max_tokens: int = Field(..., gt=0, description="Suggested max tokens per request")


class ModelRecommendation(BaseModel):
    """Single model recommendation with reasoning and configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_id: str = Field(..., description="Model identifier from OpenRouter catalog")
    reasoning: str = Field(
        ..., description="Detailed reasoning for this recommendation"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    suggested_config: SuggestedConfig = Field(
        ..., description="Suggested configuration parameters"
    )
    estimated_cost_per_1k: float = Field(
        ..., ge=0.0, description="Estimated cost per 1K tokens"
    )


class RecommendationResponse(BaseModel):
    """Complete response containing top model recommendations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    recommendations: list[ModelRecommendation] = Field(
        ..., description="Top 3 model recommendations"
    )
    analysis_summary: str = Field(
        ..., description="Overall analysis summary of the recommendations"
    )


if __name__ == "__main__":
    # Example usage
    sample_input = UseCaseInput(
        description="I need a fast, affordable chatbot for customer support",
        max_cost=0.01,
        min_speed=50.0,
        context_length_required=4096,
    )

    sample_config = SuggestedConfig(
        temperature=0.7,
        top_p=0.9,
        max_tokens=1000,
    )

    sample_recommendation = ModelRecommendation(
        model_id="openai/gpt-3.5-turbo",
        reasoning="This model provides excellent speed and cost efficiency for customer support chatbots.",
        confidence_score=0.95,
        suggested_config=sample_config,
        estimated_cost_per_1k=0.002,
    )

    sample_response = RecommendationResponse(
        recommendations=[sample_recommendation],
        analysis_summary="Recommended GPT-3.5 Turbo for its balance of speed, cost, and quality.",
    )

    print("UseCaseInput:")
    print(sample_input.model_dump())

    print("\nModelRecommendation:")
    print(sample_recommendation.model_dump())

    print("\nRecommendationResponse:")
    print(sample_response.model_dump())
