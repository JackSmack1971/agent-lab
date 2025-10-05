"""Unit tests for the model matchmaker component."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.components.model_matchmaker import (format_recommendation_card,
                                             get_recommendations_async,
                                             validate_context_length,
                                             validate_max_cost,
                                             validate_min_speed,
                                             validate_use_case_description)
from src.models.recommendation import (ModelRecommendation,
                                       RecommendationResponse, SuggestedConfig)


class TestModelMatchmakerValidation:
    """Test validation functions for the model matchmaker."""

    def test_validate_use_case_description_valid(self):
        """Test valid use case description."""
        result = validate_use_case_description("I need a chatbot for customer support")
        assert result["is_valid"] is True
        assert "valid" in result["message"]

    def test_validate_use_case_description_empty(self):
        """Test empty use case description."""
        result = validate_use_case_description("")
        assert result["is_valid"] is False
        assert "required" in result["message"]

    def test_validate_use_case_description_whitespace(self):
        """Test whitespace-only use case description."""
        result = validate_use_case_description("   ")
        assert result["is_valid"] is False
        assert "required" in result["message"]

    def test_validate_use_case_description_too_long(self):
        """Test use case description that exceeds character limit."""
        long_description = "A" * 501
        result = validate_use_case_description(long_description)
        assert result["is_valid"] is False
        assert "500 characters" in result["message"]

    def test_validate_max_cost_valid(self):
        """Test valid max cost."""
        result = validate_max_cost("0.01")
        assert result["is_valid"] is True
        assert "valid" in result["message"]

    def test_validate_max_cost_empty(self):
        """Test empty max cost (optional field)."""
        result = validate_max_cost("")
        assert result["is_valid"] is True
        assert result["message"] == ""

    def test_validate_max_cost_invalid_number(self):
        """Test invalid max cost format."""
        result = validate_max_cost("not-a-number")
        assert result["is_valid"] is False
        assert "number" in result["message"]

    def test_validate_max_cost_negative(self):
        """Test negative max cost."""
        result = validate_max_cost("-0.01")
        assert result["is_valid"] is False
        assert "greater than 0" in result["message"]

    def test_validate_max_cost_too_high(self):
        """Test max cost above limit."""
        result = validate_max_cost("2.0")
        assert result["is_valid"] is False
        assert "$1.00" in result["message"]

    def test_validate_min_speed_valid(self):
        """Test valid min speed."""
        result = validate_min_speed("50")
        assert result["is_valid"] is True
        assert "valid" in result["message"]

    def test_validate_min_speed_empty(self):
        """Test empty min speed (optional field)."""
        result = validate_min_speed("")
        assert result["is_valid"] is True
        assert result["message"] == ""

    def test_validate_min_speed_invalid(self):
        """Test invalid min speed."""
        result = validate_min_speed("not-a-number")
        assert result["is_valid"] is False
        assert "number" in result["message"]

    def test_validate_min_speed_negative(self):
        """Test negative min speed."""
        result = validate_min_speed("-10")
        assert result["is_valid"] is False
        assert "greater than 0" in result["message"]

    def test_validate_min_speed_too_high(self):
        """Test min speed above limit."""
        result = validate_min_speed("2000")
        assert result["is_valid"] is False
        assert "1000 tokens/second" in result["message"]

    def test_validate_context_length_valid(self):
        """Test valid context length."""
        result = validate_context_length("4096")
        assert result["is_valid"] is True
        assert "valid" in result["message"]

    def test_validate_context_length_empty(self):
        """Test empty context length (optional field)."""
        result = validate_context_length("")
        assert result["is_valid"] is True
        assert result["message"] == ""

    def test_validate_context_length_invalid(self):
        """Test invalid context length."""
        result = validate_context_length("not-a-number")
        assert result["is_valid"] is False
        assert "whole number" in result["message"]

    def test_validate_context_length_negative(self):
        """Test negative context length."""
        result = validate_context_length("-1000")
        assert result["is_valid"] is False
        assert "greater than 0" in result["message"]

    def test_validate_context_length_too_high(self):
        """Test context length above limit."""
        result = validate_context_length("300000")
        assert result["is_valid"] is False
        assert "200,000 tokens" in result["message"]


class TestRecommendationFormatting:
    """Test recommendation formatting functions."""

    def test_format_recommendation_card(self):
        """Test formatting a recommendation as HTML card."""
        recommendation = ModelRecommendation(
            model_id="openai/gpt-4o",
            reasoning="Best overall model for complex tasks",
            confidence_score=0.95,
            suggested_config=SuggestedConfig(
                temperature=0.7,
                top_p=0.9,
                max_tokens=2000,
            ),
            estimated_cost_per_1k=0.01,
        )

        html = format_recommendation_card(recommendation, 0)

        assert "openai/gpt-4o" in html
        assert "95.0%" in html
        assert "$0.0100" in html
        assert "Best overall model" in html
        assert "Temperature: 0.7" in html
        assert "Apply Config" in html


class TestGetRecommendationsAsync:
    """Test the async recommendation fetching function."""

    @pytest.mark.asyncio
    @patch("src.components.model_matchmaker.analyze_use_case")
    async def test_get_recommendations_success(self, mock_analyze):
        """Test successful recommendation fetching."""
        # Mock the recommendation service
        mock_response = RecommendationResponse(
            recommendations=[
                ModelRecommendation(
                    model_id="openai/gpt-4o",
                    reasoning="Best model",
                    confidence_score=0.9,
                    suggested_config=SuggestedConfig(
                        temperature=0.7, top_p=0.9, max_tokens=1000
                    ),
                    estimated_cost_per_1k=0.01,
                )
            ],
            analysis_summary="Recommended GPT-4o",
        )
        mock_analyze.return_value = mock_response

        result_html, error_msg = await get_recommendations_async(
            description="I need a good model",
            max_cost="0.02",
            min_speed="",
            context_length="",
        )

        assert error_msg == ""
        assert "Recommended GPT-4o" in result_html
        assert "openai/gpt-4o" in result_html
        mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recommendations_validation_error(self):
        """Test validation error handling."""
        result_html, error_msg = await get_recommendations_async(
            description="",  # Empty description
            max_cost="0.02",
            min_speed="",
            context_length="",
        )

        assert result_html == ""
        assert "required" in error_msg

    @pytest.mark.asyncio
    async def test_get_recommendations_invalid_cost(self):
        """Test invalid cost validation."""
        result_html, error_msg = await get_recommendations_async(
            description="I need a model",
            max_cost="invalid",
            min_speed="",
            context_length="",
        )

        assert result_html == ""
        assert "number" in error_msg

    @pytest.mark.asyncio
    @patch("src.components.model_matchmaker.analyze_use_case")
    async def test_get_recommendations_service_error(self, mock_analyze):
        """Test service error handling."""
        mock_analyze.side_effect = ValueError("Service unavailable")

        result_html, error_msg = await get_recommendations_async(
            description="I need a model",
            max_cost="",
            min_speed="",
            context_length="",
        )

        assert result_html == ""
        assert "Failed to get recommendations" in error_msg

    @pytest.mark.asyncio
    @patch("src.components.model_matchmaker.analyze_use_case")
    async def test_get_recommendations_with_constraints(self, mock_analyze):
        """Test recommendations with all constraints provided."""
        mock_response = RecommendationResponse(
            recommendations=[
                ModelRecommendation(
                    model_id="openai/gpt-3.5-turbo",
                    reasoning="Fast and affordable",
                    confidence_score=0.85,
                    suggested_config=SuggestedConfig(
                        temperature=0.7, top_p=0.9, max_tokens=1000
                    ),
                    estimated_cost_per_1k=0.002,
                )
            ],
            analysis_summary="Recommended based on constraints",
        )
        mock_analyze.return_value = mock_response

        result_html, error_msg = await get_recommendations_async(
            description="I need a fast, cheap model",
            max_cost="0.01",
            min_speed="50",
            context_length="4096",
        )

        assert error_msg == ""
        assert "Fast and affordable" in result_html
        # Verify the constraints were passed correctly
        call_args = mock_analyze.call_args[0][0]  # First positional argument
        assert call_args.description == "I need a fast, cheap model"
        assert call_args.max_cost == 0.01
        assert call_args.min_speed == 50.0
        assert call_args.context_length_required == 4096


class TestComponentIntegration:
    """Test component integration aspects."""

    @patch("src.components.model_matchmaker.create_model_matchmaker_tab")
    def test_create_model_matchmaker_tab_basic(self, mock_create):
        """Test basic tab creation."""
        mock_tab = MagicMock()
        mock_create.return_value = mock_tab

        from src.components.model_matchmaker import create_model_matchmaker_tab

        result = create_model_matchmaker_tab()

        assert result == mock_tab
        mock_create.assert_called_once_with()

    @patch("src.components.model_matchmaker.create_model_matchmaker_tab")
    def test_create_model_matchmaker_tab_with_callback(self, mock_create):
        """Test tab creation with callback."""
        mock_tab = MagicMock()
        mock_create.return_value = mock_tab
        mock_callback = MagicMock()

        from src.components.model_matchmaker import create_model_matchmaker_tab

        result = create_model_matchmaker_tab(mock_callback)

        assert result == mock_tab
        mock_create.assert_called_once_with(mock_callback)
