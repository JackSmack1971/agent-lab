"""AI Model Matchmaker service for recommending optimal models based on use cases."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from pydantic import ValidationError

from services.catalog import get_models
from src.models.recommendation import (
    ModelRecommendation,
    RecommendationResponse,
    SuggestedConfig,
    UseCaseInput,
)

# Logger configured at module level to avoid leaking sensitive data.
logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 30.0
CACHE_TTL = timedelta(hours=1)

RECOMMENDATION_SYSTEM_PROMPT = """
You are an AI model selection expert. Analyze the user's use case and recommend
the top 3 models from the OpenRouter catalog that best fit their needs.
Consider: speed, cost, quality, context window, tool support.
Return JSON with recommendations including detailed reasoning.

Available models and their characteristics:
{available_models}

User constraints:
{max_cost_constraint}
{min_speed_constraint}
{context_length_constraint}

Response format:
{{
  "recommendations": [
    {{
      "model_id": "model_identifier",
      "reasoning": "detailed explanation why this model fits",
      "confidence_score": 0.95,
      "suggested_config": {{
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 1000
      }},
      "estimated_cost_per_1k": 0.002
    }}
  ],
  "analysis_summary": "Overall analysis of recommendations"
}}
""".strip()

# Global cache for recommendations
_cached_recommendations: Optional[
    dict[str, tuple[RecommendationResponse, datetime]]
] = None


def _build_system_prompt(use_case: UseCaseInput) -> str:
    """Build the system prompt with available models and user constraints."""

    models, _, _ = get_models()
    model_descriptions = []

    for model in models[:20]:  # Limit to top 20 models for prompt size
        desc = f"- {model.id}: {model.display_name} by {model.provider}"
        if model.description:
            desc += f" - {model.description[:100]}..."
        if model.input_price is not None and model.output_price is not None:
            desc += f" (costs: ${model.input_price:.4f}/${model.output_price:.4f} per 1K tokens)"
        model_descriptions.append(desc)

    available_models = "\n".join(model_descriptions)

    constraints = []
    if use_case.max_cost is not None:
        constraints.append(f"- Maximum cost: ${use_case.max_cost:.4f} per 1K tokens")
    if use_case.min_speed is not None:
        constraints.append(f"- Minimum speed: {use_case.min_speed} tokens/second")
    if use_case.context_length_required is not None:
        constraints.append(
            f"- Minimum context length: {use_case.context_length_required} tokens"
        )

    cost_constraint = (
        constraints[0] if len(constraints) > 0 else "- No cost limit specified"
    )
    speed_constraint = (
        constraints[1] if len(constraints) > 1 else "- No speed requirement specified"
    )
    context_constraint = (
        constraints[2]
        if len(constraints) > 2
        else "- No context length requirement specified"
    )

    return RECOMMENDATION_SYSTEM_PROMPT.format(
        available_models=available_models,
        max_cost_constraint=cost_constraint,
        min_speed_constraint=speed_constraint,
        context_length_constraint=context_constraint,
    )


def _call_gpt4_for_recommendations(use_case: UseCaseInput) -> RecommendationResponse:
    """Call GPT-4 via OpenRouter to get model recommendations."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    system_prompt = _build_system_prompt(use_case)

    payload = {
        "model": "openai/gpt-4o",  # Using GPT-4o for better analysis
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Use case: {use_case.description}"},
        ],
        "temperature": 0.3,  # Lower temperature for more consistent recommendations
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://agent-lab.example.com",  # Required by OpenRouter
        "X-Title": "Agent Lab Model Matchmaker",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed_response = json.loads(content)

        # Validate and parse the recommendations
        recommendations = []
        for rec_data in parsed_response.get("recommendations", [])[:3]:  # Top 3 only
            try:
                recommendation = ModelRecommendation(**rec_data)
                recommendations.append(recommendation)
            except ValidationError as exc:
                logger.warning("Invalid recommendation data: %s", exc)
                continue

        if not recommendations:
            raise ValueError("No valid recommendations received from GPT-4")

        analysis_summary = parsed_response.get(
            "analysis_summary", "Recommendations generated based on your use case."
        )

        return RecommendationResponse(
            recommendations=recommendations,
            analysis_summary=analysis_summary,
        )

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValidationError) as exc:
        logger.error("Failed to get recommendations from GPT-4: %s", exc)
        raise ValueError(f"Failed to generate recommendations: {exc}") from exc


def _get_fallback_recommendations(use_case: UseCaseInput) -> RecommendationResponse:
    """Provide fallback recommendations when GPT-4 is unavailable."""

    # Simple rule-based fallback based on use case keywords
    description_lower = use_case.description.lower()

    recommendations = []

    if "fast" in description_lower or "speed" in description_lower:
        # Recommend GPT-3.5 Turbo for speed
        recommendations.append(
            ModelRecommendation(
                model_id="openai/gpt-3.5-turbo",
                reasoning="GPT-3.5 Turbo offers excellent speed and cost efficiency, ideal for fast response requirements.",
                confidence_score=0.85,
                suggested_config=SuggestedConfig(
                    temperature=0.7, top_p=0.9, max_tokens=1000
                ),
                estimated_cost_per_1k=0.002,
            )
        )
    elif (
        "quality" in description_lower
        or "best" in description_lower
        or "high" in description_lower
    ):
        # Recommend GPT-4 for quality
        recommendations.append(
            ModelRecommendation(
                model_id="openai/gpt-4o",
                reasoning="GPT-4o provides the highest quality responses with advanced reasoning capabilities.",
                confidence_score=0.95,
                suggested_config=SuggestedConfig(
                    temperature=0.7, top_p=0.9, max_tokens=2000
                ),
                estimated_cost_per_1k=0.01,
            )
        )
    elif (
        "long" in description_lower
        or "document" in description_lower
        or "context" in description_lower
    ):
        # Recommend Claude for long context
        recommendations.append(
            ModelRecommendation(
                model_id="anthropic/claude-3-opus",
                reasoning="Claude 3 Opus has excellent context handling and is suitable for long document analysis.",
                confidence_score=0.90,
                suggested_config=SuggestedConfig(
                    temperature=0.3, top_p=0.9, max_tokens=4000
                ),
                estimated_cost_per_1k=0.015,
            )
        )

    # Always add default recommendations to fill up to 3
    default_recommendations = [
        ModelRecommendation(
            model_id="openai/gpt-4o-mini",
            reasoning="Balanced model offering good quality at reasonable cost.",
            confidence_score=0.80,
            suggested_config=SuggestedConfig(
                temperature=0.7, top_p=0.9, max_tokens=1000
            ),
            estimated_cost_per_1k=0.00015,
        ),
        ModelRecommendation(
            model_id="anthropic/claude-3-haiku",
            reasoning="Fast and efficient model for general use cases.",
            confidence_score=0.75,
            suggested_config=SuggestedConfig(
                temperature=0.7, top_p=0.9, max_tokens=1000
            ),
            estimated_cost_per_1k=0.00025,
        ),
        ModelRecommendation(
            model_id="meta-llama/llama-3-70b-instruct",
            reasoning="Open-source model with good performance for various tasks.",
            confidence_score=0.70,
            suggested_config=SuggestedConfig(
                temperature=0.7, top_p=0.9, max_tokens=1000
            ),
            estimated_cost_per_1k=0.002,
        ),
    ]

    # Add defaults to fill up to 3 recommendations
    for default_rec in default_recommendations:
        if len(recommendations) >= 3:
            break
        # Avoid duplicates
        if not any(rec.model_id == default_rec.model_id for rec in recommendations):
            recommendations.append(default_rec)

    return RecommendationResponse(
        recommendations=recommendations[:3],  # Ensure max 3
        analysis_summary="Fallback recommendations based on basic use case analysis. GPT-4 analysis unavailable.",
    )


def analyze_use_case(use_case: UseCaseInput) -> RecommendationResponse:
    """Analyze a use case and return top 3 model recommendations.

    Args:
        use_case: The use case input with description and optional constraints.

    Returns:
        RecommendationResponse containing top 3 recommendations and analysis summary.

    Raises:
        ValueError: If the use case description is empty or API calls fail.
    """
    global _cached_recommendations

    if not use_case.description or not use_case.description.strip():
        raise ValueError("Use case description cannot be empty")

    # Check cache first
    cache_key = f"{use_case.description}_{use_case.max_cost}_{use_case.min_speed}_{use_case.context_length_required}"
    if _cached_recommendations and cache_key in _cached_recommendations:
        cached_response, cached_time = _cached_recommendations[cache_key]
        if datetime.now(timezone.utc) - cached_time < CACHE_TTL:
            logger.info("Returning cached recommendations for use case")
            return cached_response

    try:
        # Try GPT-4 analysis first
        response = _call_gpt4_for_recommendations(use_case)
        logger.info("Successfully generated recommendations using GPT-4")
    except Exception as exc:
        logger.warning("GPT-4 recommendation failed, using fallback: %s", exc)
        # Fallback to rule-based recommendations
        response = _get_fallback_recommendations(use_case)

    # Cache the result
    if _cached_recommendations is None:
        _cached_recommendations = {}
    _cached_recommendations[cache_key] = (response, datetime.now(timezone.utc))

    return response


if __name__ == "__main__":
    # Test the service
    test_use_case = UseCaseInput(
        description="I need a fast, affordable chatbot for customer support",
        max_cost=0.01,
        min_speed=None,
        context_length_required=None,
    )

    try:
        response = analyze_use_case(test_use_case)
        print(f"Got {len(response.recommendations)} recommendations")
        print(f"Summary: {response.analysis_summary}")
        for i, rec in enumerate(response.recommendations, 1):
            print(f"{i}. {rec.model_id} (confidence: {rec.confidence_score:.2f})")
            print(f"   Cost: ${rec.estimated_cost_per_1k:.4f} per 1K tokens")
            print(f"   Reasoning: {rec.reasoning[:100]}...")
    except Exception as exc:
        print(f"Error: {exc}")
