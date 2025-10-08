"""Enhanced model recommender service for comparison and ranking features."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from services.catalog import ModelInfo, get_models
from src.models.recommendation import ModelRecommendation, RecommendationResponse, UseCaseInput
from src.services.recommendation_service import analyze_use_case

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 30.0
CACHE_TTL = timedelta(hours=1)

# Global cache for comparison results
_comparison_cache: Optional[Dict[str, Tuple[ModelComparisonResult, datetime]]] = None


class ModelDetail(BaseModel):
    """Detailed model information for comparison."""

    model_id: str = Field(..., description="Model identifier")
    display_name: str = Field(..., description="Human-readable model name")
    provider: str = Field(..., description="Model provider")
    description: Optional[str] = Field(None, description="Model description")
    input_price: Optional[float] = Field(None, description="Input token price per 1K tokens")
    output_price: Optional[float] = Field(None, description="Output token price per 1K tokens")
    context_window: Optional[int] = Field(None, description="Context window size")
    average_cost_per_1k: Optional[float] = Field(None, description="Average cost per 1K tokens")
    performance_score: Optional[float] = Field(None, description="Performance score (0-1)")


class ModelComparisonRequest(BaseModel):
    """Request model for comparing multiple models."""

    model_ids: List[str] = Field(..., description="List of model IDs to compare")
    use_case_description: str = Field(..., description="Use case description for recommendations")
    include_cost_analysis: bool = Field(True, description="Include cost analysis in results")
    include_performance_metrics: bool = Field(True, description="Include performance metrics")


class ModelComparisonResult(BaseModel):
    """Result model for model comparison operations."""

    model_details: List[ModelDetail] = Field(..., description="Detailed information for each model")
    recommendations: List[ModelRecommendation] = Field(..., description="Top recommendations with reasoning")
    cost_analysis: Dict[str, float] = Field(default_factory=dict, description="Cost analysis metrics")
    performance_analysis: Dict[str, float] = Field(default_factory=dict, description="Performance analysis metrics")
    comparison_summary: str = Field(..., description="Overall comparison summary")


def _calculate_average_cost(input_price: Optional[float], output_price: Optional[float]) -> Optional[float]:
    """Calculate average cost per 1K tokens."""
    if input_price is not None and output_price is not None:
        return (input_price + output_price) / 2
    return None


def _estimate_performance_score(model: ModelInfo) -> float:
    """Estimate performance score based on model characteristics (simplified heuristic)."""
    score = 0.5  # Base score

    # Provider-based scoring
    if model.provider == "openai":
        score += 0.2
    elif model.provider == "anthropic":
        score += 0.15
    elif model.provider == "google":
        score += 0.1

    # Cost-based adjustment (lower cost = slightly higher score)
    avg_cost = _calculate_average_cost(model.input_price, model.output_price)
    if avg_cost and avg_cost < 0.01:
        score += 0.1
    elif avg_cost and avg_cost > 0.05:
        score -= 0.1

    return min(max(score, 0.0), 1.0)


def get_model_comparison_data(model_ids: List[str]) -> List[ModelDetail]:
    """Get detailed model data for comparison."""
    models, _, _ = get_models()

    model_details = []
    for model_id in model_ids:
        model_info = next((m for m in models if m.id == model_id), None)
        if model_info:
            model_detail = ModelDetail(
                model_id=model_info.id,
                display_name=model_info.display_name,
                provider=model_info.provider,
                description=model_info.description,
                input_price=model_info.input_price,
                output_price=model_info.output_price,
                context_window=None,  # Would need to be fetched from API or hardcoded
                average_cost_per_1k=_calculate_average_cost(model_info.input_price, model_info.output_price),
                performance_score=_estimate_performance_score(model_info),
            )
            model_details.append(model_detail)

    return model_details


async def compare_models(request: ModelComparisonRequest) -> ModelComparisonResult:
    """Compare multiple models and generate recommendations."""
    global _comparison_cache

    # Create cache key
    cache_key = f"{','.join(sorted(request.model_ids))}_{request.use_case_description}_{request.include_cost_analysis}_{request.include_performance_metrics}"

    # Check cache
    if _comparison_cache and cache_key in _comparison_cache:
        cached_result, cached_time = _comparison_cache[cache_key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            logger.info("Returning cached comparison results")
            return cached_result

    try:
        # Get model details
        model_details = get_model_comparison_data(request.model_ids)

        if not model_details:
            raise ValueError("No valid models found for comparison")

        # Generate recommendations using existing service
        use_case_input = UseCaseInput(
            description=request.use_case_description,
            max_cost=None,  # No cost constraint for comparison
            min_speed=None,
            context_length_required=None,
        )

        recommendation_response = await asyncio.get_event_loop().run_in_executor(
            None, analyze_use_case, use_case_input
        )

        # Filter recommendations to only include requested models
        filtered_recommendations = [
            rec for rec in recommendation_response.recommendations
            if rec.model_id in request.model_ids
        ]

        # If no recommendations match, create basic ones
        if not filtered_recommendations:
            filtered_recommendations = _create_basic_recommendations(model_details, request.use_case_description)

        # Calculate cost analysis
        cost_analysis = {}
        if request.include_cost_analysis:
            costs = [m.average_cost_per_1k for m in model_details if m.average_cost_per_1k is not None]
            if costs:
                cost_analysis = {
                    "average_cost": sum(costs) / len(costs),
                    "min_cost": min(costs),
                    "max_cost": max(costs),
                    "cost_range": max(costs) - min(costs),
                }

        # Calculate performance analysis
        performance_analysis = {}
        if request.include_performance_metrics:
            scores = [m.performance_score for m in model_details if m.performance_score is not None]
            if scores:
                performance_analysis = {
                    "average_score": sum(scores) / len(scores),
                    "best_score": max(scores),
                    "worst_score": min(scores),
                }

        # Generate comparison summary
        summary = _generate_comparison_summary(model_details, filtered_recommendations)

        result = ModelComparisonResult(
            model_details=model_details,
            recommendations=filtered_recommendations,
            cost_analysis=cost_analysis,
            performance_analysis=performance_analysis,
            comparison_summary=summary,
        )

        # Cache the result
        if _comparison_cache is None:
            _comparison_cache = {}
        _comparison_cache[cache_key] = (result, datetime.now(timezone.utc))

        return result

    except Exception as exc:
        logger.error("Failed to compare models: %s", exc)
        raise ValueError(f"Model comparison failed: {exc}") from exc


def _create_basic_recommendations(model_details: List[ModelDetail], use_case: str) -> List[ModelRecommendation]:
    """Create basic recommendations when AI analysis is unavailable."""
    from src.models.recommendation import SuggestedConfig

    recommendations = []

    # Sort by performance score and cost
    sorted_models = sorted(
        model_details,
        key=lambda m: (
            -(m.performance_score or 0),  # Higher score first
            m.average_cost_per_1k or 999,  # Lower cost first
        )
    )

    for i, model in enumerate(sorted_models[:3]):  # Top 3
        confidence = max(0.6 - (i * 0.1), 0.4)  # Decreasing confidence

        reasoning = f"{model.display_name} is recommended for {use_case.lower()} "
        if model.performance_score and model.performance_score > 0.7:
            reasoning += "due to its strong performance characteristics."
        elif model.average_cost_per_1k and model.average_cost_per_1k < 0.02:
            reasoning += "due to its cost efficiency."
        else:
            reasoning += "as a balanced option."

        recommendation = ModelRecommendation(
            model_id=model.model_id,
            reasoning=reasoning,
            confidence_score=confidence,
            suggested_config=SuggestedConfig(
                temperature=0.7,
                top_p=0.9,
                max_tokens=1000,
            ),
            estimated_cost_per_1k=model.average_cost_per_1k or 0.01,
        )
        recommendations.append(recommendation)

    return recommendations


def _generate_comparison_summary(model_details: List[ModelDetail], recommendations: List[ModelRecommendation]) -> str:
    """Generate a human-readable comparison summary."""
    if not model_details:
        return "No models to compare."

    provider_counts = {}
    for model in model_details:
        provider_counts[model.provider] = provider_counts.get(model.provider, 0) + 1

    provider_summary = ", ".join([f"{count} {provider}" for provider, count in provider_counts.items()])

    cost_range = ""
    costs = [m.average_cost_per_1k for m in model_details if m.average_cost_per_1k is not None]
    if costs:
        cost_range = f" with costs ranging from ${min(costs):.4f} to ${max(costs):.4f} per 1K tokens"

    summary = f"Comparing {len(model_details)} models from {provider_summary}{cost_range}. "

    if recommendations:
        top_model = recommendations[0].model_id.split('/')[-1]
        summary += f"The top recommendation is {top_model} with {recommendations[0].confidence_score:.1%} confidence."

    return summary


if __name__ == "__main__":
    # Test the service
    async def test():
        request = ModelComparisonRequest(
            model_ids=["openai/gpt-4o", "anthropic/claude-3-opus", "meta-llama/llama-3-70b-instruct"],
            use_case_description="General purpose AI assistant for coding and analysis",
            include_cost_analysis=True,
            include_performance_metrics=True,
        )

        try:
            result = await compare_models(request)
            print(f"Compared {len(result.model_details)} models")
            print(f"Summary: {result.comparison_summary}")
            print(f"Top recommendation: {result.recommendations[0].model_id if result.recommendations else 'None'}")
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())