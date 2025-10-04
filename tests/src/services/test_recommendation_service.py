"""Unit tests for the recommendation service."""

from __future__ import annotations

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.models.recommendation import (
    UseCaseInput,
    ModelRecommendation,
    RecommendationResponse,
    SuggestedConfig,
)
from src.services.recommendation_service import (
    analyze_use_case,
    _get_fallback_recommendations,
    _build_system_prompt,
    _call_gpt4_for_recommendations,
)


class TestRecommendationService:
    """Test cases for the recommendation service."""

    def test_build_system_prompt(self):
        """Test building the system prompt with available models and constraints."""
        use_case = UseCaseInput(
            description="I need a fast, affordable chatbot for customer support",
            max_cost=0.01,
            min_speed=50.0,
            context_length_required=4096,
        )

        # Mock the get_models function
        with patch('src.services.recommendation_service.get_models') as mock_get_models:
            mock_get_models.return_value = ([
                Mock(id="openai/gpt-3.5-turbo", display_name="GPT-3.5 Turbo", provider="openai",
                     description="Fast and affordable model", input_price=0.001, output_price=0.002),
                Mock(id="anthropic/claude-3-haiku", display_name="Claude 3 Haiku", provider="anthropic",
                     description="Efficient model", input_price=0.002, output_price=0.004),
            ], "dynamic", datetime.now(timezone.utc))

            prompt = _build_system_prompt(use_case)

            assert "Maximum cost: $0.0100 per 1K tokens" in prompt
            assert "Minimum speed: 50.0 tokens/second" in prompt
            assert "Minimum context length: 4096 tokens" in prompt
            assert "openai/gpt-3.5-turbo" in prompt
            assert "anthropic/claude-3-haiku" in prompt

    @patch('src.services.recommendation_service._call_gpt4_for_recommendations')
    def test_analyze_use_case_success(self, mock_gpt4_call):
        """Test successful use case analysis."""
        use_case = UseCaseInput(
            description="I need a fast chatbot",
            max_cost=0.01,
            min_speed=None,
            context_length_required=None,
        )

        mock_response = RecommendationResponse(
            recommendations=[
                ModelRecommendation(
                    model_id="openai/gpt-3.5-turbo",
                    reasoning="Fast and affordable",
                    confidence_score=0.9,
                    suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                    estimated_cost_per_1k=0.002,
                )
            ],
            analysis_summary="Recommended fast model",
        )
        mock_gpt4_call.return_value = mock_response

        result = analyze_use_case(use_case)

        assert len(result.recommendations) == 1
        assert result.recommendations[0].model_id == "openai/gpt-3.5-turbo"
        assert result.analysis_summary == "Recommended fast model"
        mock_gpt4_call.assert_called_once_with(use_case)

    @patch('src.services.recommendation_service._call_gpt4_for_recommendations')
    def test_analyze_use_case_gpt4_fails_uses_fallback(self, mock_gpt4_call):
        """Test fallback when GPT-4 fails."""
        use_case = UseCaseInput(description="I need a fast chatbot")

        mock_gpt4_call.side_effect = ValueError("API error")

        result = analyze_use_case(use_case)

        # Should get fallback recommendations
        assert len(result.recommendations) >= 1
        assert "Fallback recommendations" in result.analysis_summary
        mock_gpt4_call.assert_called_once_with(use_case)

    def test_analyze_use_case_empty_description(self):
        """Test error handling for empty description."""
        use_case = UseCaseInput(description="")

        with pytest.raises(ValueError, match="Use case description cannot be empty"):
            analyze_use_case(use_case)

    def test_analyze_use_case_whitespace_description(self):
        """Test error handling for whitespace-only description."""
        use_case = UseCaseInput(description="   ")

        with pytest.raises(ValueError, match="Use case description cannot be empty"):
            analyze_use_case(use_case)

    @patch('src.services.recommendation_service.httpx.Client')
    @patch('src.services.recommendation_service.os.getenv')
    def test_call_gpt4_for_recommendations_success(self, mock_getenv, mock_client_class):
        """Test successful GPT-4 API call."""
        mock_getenv.return_value = "test-api-key"

        # Mock the HTTP client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "recommendations": [{
                            "model_id": "openai/gpt-4o",
                            "reasoning": "Best overall model",
                            "confidence_score": 0.95,
                            "suggested_config": {
                                "temperature": 0.7,
                                "top_p": 0.9,
                                "max_tokens": 2000
                            },
                            "estimated_cost_per_1k": 0.01
                        }],
                        "analysis_summary": "Recommended GPT-4o"
                    })
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        use_case = UseCaseInput(description="I need the best model")

        result = _call_gpt4_for_recommendations(use_case)

        assert len(result.recommendations) == 1
        assert result.recommendations[0].model_id == "openai/gpt-4o"
        assert result.analysis_summary == "Recommended GPT-4o"

    @patch('src.services.recommendation_service.os.getenv')
    def test_call_gpt4_for_recommendations_no_api_key(self, mock_getenv):
        """Test error when API key is not set."""
        mock_getenv.return_value = None

        use_case = UseCaseInput(description="test")

        with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is required"):
            _call_gpt4_for_recommendations(use_case)

    def test_get_fallback_recommendations_fast_use_case(self):
        """Test fallback recommendations for fast use case."""
        use_case = UseCaseInput(description="I need a fast, affordable chatbot")

        result = _get_fallback_recommendations(use_case)

        assert len(result.recommendations) == 3
        assert result.recommendations[0].model_id == "openai/gpt-3.5-turbo"
        assert "Fallback recommendations" in result.analysis_summary

    def test_get_fallback_recommendations_quality_use_case(self):
        """Test fallback recommendations for quality-focused use case."""
        use_case = UseCaseInput(description="I want the highest quality model, cost is not a concern")

        result = _get_fallback_recommendations(use_case)

        assert len(result.recommendations) == 3
        assert result.recommendations[0].model_id == "openai/gpt-4o"

    def test_get_fallback_recommendations_long_context(self):
        """Test fallback recommendations for long context use case."""
        use_case = UseCaseInput(description="I need to analyze very long documents (50k tokens)")

        result = _get_fallback_recommendations(use_case)

        assert len(result.recommendations) == 3
        assert result.recommendations[0].model_id == "anthropic/claude-3-opus"

    def test_get_fallback_recommendations_generic(self):
        """Test fallback recommendations for generic use case."""
        use_case = UseCaseInput(description="I need an AI assistant")

        result = _get_fallback_recommendations(use_case)

        assert len(result.recommendations) == 3
        # Should have default recommendations
        assert result.recommendations[0].model_id == "openai/gpt-4o-mini"

    @patch('src.services.recommendation_service._call_gpt4_for_recommendations')
    def test_caching_behavior(self, mock_gpt4_call):
        """Test that recommendations are cached properly."""
        use_case = UseCaseInput(description="test caching", max_cost=0.01)

        mock_response = RecommendationResponse(
            recommendations=[
                ModelRecommendation(
                    model_id="openai/gpt-3.5-turbo",
                    reasoning="Cached recommendation",
                    confidence_score=0.8,
                    suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                    estimated_cost_per_1k=0.002,
                )
            ],
            analysis_summary="Cached response",
        )
        mock_gpt4_call.return_value = mock_response

        # First call
        result1 = analyze_use_case(use_case)
        assert mock_gpt4_call.call_count == 1

        # Second call with same parameters should use cache
        result2 = analyze_use_case(use_case)
        assert mock_gpt4_call.call_count == 1  # Should not call again

        assert result1.recommendations[0].model_id == result2.recommendations[0].model_id

    def test_recommendation_models_validation(self):
        """Test that recommendation models validate properly."""
        # Valid recommendation
        rec = ModelRecommendation(
            model_id="test-model",
            reasoning="Test reasoning",
            confidence_score=0.8,
            suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
            estimated_cost_per_1k=0.005,
        )
        assert rec.model_id == "test-model"
        assert rec.confidence_score == 0.8

        # Invalid confidence score
        with pytest.raises(ValueError):
            ModelRecommendation(
                model_id="test-model",
                reasoning="Test",
                confidence_score=1.5,  # Invalid: > 1.0
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.005,
            )

        # Invalid temperature
        with pytest.raises(ValueError):
            SuggestedConfig(temperature=3.0, top_p=0.9, max_tokens=1000)  # Invalid: > 2.0