"""Integration tests for model comparison dashboard functionality."""

import pytest
from unittest.mock import patch, MagicMock

from src.services.model_recommender import ModelComparisonRequest, ModelComparisonResult, ModelDetail
from src.models.recommendation import ModelRecommendation, SuggestedConfig


class TestModelComparisonIntegration:
    """Integration tests for the complete model comparison workflow."""

    @patch('src.services.model_recommender.analyze_use_case')
    @patch('src.services.model_recommender.get_models')
    @pytest.mark.asyncio
    async def test_full_comparison_workflow(self, mock_get_models, mock_analyze):
        """Test the complete model comparison workflow from request to result."""
        from src.services.model_recommender import compare_models

        # Mock the model catalog
        mock_models = [
            MagicMock(id="openai/gpt-4", display_name="GPT-4", provider="openai",
                     input_price=0.01, output_price=0.03, description="Advanced model"),
            MagicMock(id="anthropic/claude-3-opus", display_name="Claude 3 Opus", provider="anthropic",
                     input_price=0.015, output_price=0.075, description="Safety-focused model"),
            MagicMock(id="meta-llama/llama-3-70b-instruct", display_name="Llama 3 70B", provider="meta",
                     input_price=0.002, output_price=0.002, description="Open-source model"),
        ]
        mock_get_models.return_value = (mock_models, "dynamic", None)

        # Mock the recommendation response
        mock_rec_response = MagicMock()
        mock_rec_response.recommendations = [
            ModelRecommendation(
                model_id="openai/gpt-4",
                reasoning="Best for complex reasoning tasks requiring high accuracy",
                confidence_score=0.95,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=2000),
                estimated_cost_per_1k=0.02,
            ),
            ModelRecommendation(
                model_id="anthropic/claude-3-opus",
                reasoning="Excellent for safety-critical applications and long-form content",
                confidence_score=0.90,
                suggested_config=SuggestedConfig(temperature=0.3, top_p=0.9, max_tokens=4000),
                estimated_cost_per_1k=0.045,
            ),
        ]
        mock_analyze.return_value = mock_rec_response

        # Create comparison request
        request = ModelComparisonRequest(
            model_ids=["openai/gpt-4", "anthropic/claude-3-opus", "meta-llama/llama-3-70b-instruct"],
            use_case_description="Building a sophisticated AI assistant for software development and code review",
            include_cost_analysis=True,
            include_performance_metrics=True,
        )

        # Execute comparison
        result = await compare_models(request)

        # Verify result structure
        assert isinstance(result, ModelComparisonResult)
        assert len(result.model_details) == 3
        assert len(result.recommendations) == 2  # Filtered to requested models

        # Verify model details
        model_ids = [m.model_id for m in result.model_details]
        assert "openai/gpt-4" in model_ids
        assert "anthropic/claude-3-opus" in model_ids
        assert "meta-llama/llama-3-70b-instruct" in model_ids

        # Verify cost analysis
        assert "average_cost" in result.cost_analysis
        assert "min_cost" in result.cost_analysis
        assert "max_cost" in result.cost_analysis

        # Verify performance analysis
        assert "average_score" in result.performance_analysis

        # Verify recommendations
        assert result.recommendations[0].model_id == "openai/gpt-4"
        assert result.recommendations[0].confidence_score == 0.95
        assert "complex reasoning" in result.recommendations[0].reasoning

        # Verify summary
        assert "3 models" in result.comparison_summary
        assert "openai" in result.comparison_summary.lower()

    @patch('src.services.model_recommender.analyze_use_case')
    @patch('src.services.model_recommender.get_models')
    @pytest.mark.asyncio
    async def test_comparison_with_fallback_recommendations(self, mock_get_models, mock_analyze):
        """Test comparison workflow when AI analysis fails and falls back to basic recommendations."""
        from src.services.model_recommender import compare_models

        # Mock the model catalog
        mock_models = [
            MagicMock(id="openai/gpt-4", display_name="GPT-4", provider="openai",
                     input_price=0.01, output_price=0.03, description=None),
            MagicMock(id="anthropic/claude-3-haiku", display_name="Claude 3 Haiku", provider="anthropic",
                     input_price=0.00025, output_price=0.00125, description=None),
        ]
        mock_get_models.return_value = (mock_models, "dynamic", None)

        # Mock analysis to return empty recommendations (simulating failure)
        mock_rec_response = MagicMock()
        mock_rec_response.recommendations = []  # No recommendations
        mock_analyze.return_value = mock_rec_response

        # Create comparison request
        request = ModelComparisonRequest(
            model_ids=["openai/gpt-4", "anthropic/claude-3-haiku"],
            use_case_description="Simple chatbot for customer service",
            include_cost_analysis=True,
            include_performance_metrics=True,
        )

        # Execute comparison
        result = await compare_models(request)

        # Verify fallback recommendations were created
        assert len(result.recommendations) == 2  # Should have fallback recommendations
        assert result.recommendations[0].model_id == "anthropic/claude-3-haiku"  # Cheaper model first
        assert result.recommendations[1].model_id == "openai/gpt-4"  # More expensive second

        # Verify confidence scores are reasonable for fallback
        for rec in result.recommendations:
            assert 0.4 <= rec.confidence_score <= 0.6

    def test_model_detail_creation(self):
        """Test that ModelDetail objects are created correctly."""
        from src.services.model_recommender import get_model_comparison_data

        with patch('src.services.model_recommender.get_models') as mock_get_models:
            mock_models = [
                MagicMock(
                    id="test/model",
                    display_name="Test Model",
                    provider="test",
                    input_price=0.01,
                    output_price=0.02,
                    description="A test model",
                )
            ]
            mock_get_models.return_value = (mock_models, "dynamic", None)

            details = get_model_comparison_data(["test/model"])

            assert len(details) == 1
            detail = details[0]
            assert detail.model_id == "test/model"
            assert detail.display_name == "Test Model"
            assert detail.provider == "test"
            assert detail.average_cost_per_1k == 0.015  # (0.01 + 0.02) / 2
            assert detail.performance_score is not None

    def test_comparison_result_structure(self):
        """Test that ModelComparisonResult has all required fields."""
        from src.models.recommendation import SuggestedConfig

        # Create a complete comparison result
        model_details = [
            ModelDetail(
                model_id="test/model1",
                display_name="Test Model 1",
                provider="test",
                description=None,
                input_price=0.01,
                output_price=0.02,
                context_window=None,
                average_cost_per_1k=0.015,
                performance_score=0.8,
            ),
            ModelDetail(
                model_id="test/model2",
                display_name="Test Model 2",
                provider="test",
                description=None,
                input_price=0.005,
                output_price=0.015,
                context_window=None,
                average_cost_per_1k=0.01,
                performance_score=0.7,
            ),
        ]

        recommendations = [
            ModelRecommendation(
                model_id="test/model2",
                reasoning="More cost-effective option",
                confidence_score=0.85,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.01,
            ),
        ]

        result = ModelComparisonResult(
            model_details=model_details,
            recommendations=recommendations,
            cost_analysis={"average_cost": 0.0125, "min_cost": 0.01, "max_cost": 0.015},
            performance_analysis={"average_score": 0.75, "best_score": 0.8},
            comparison_summary="Comparison of 2 test models with focus on cost efficiency",
        )

        # Verify all fields are present and correct
        assert len(result.model_details) == 2
        assert len(result.recommendations) == 1
        assert result.cost_analysis["average_cost"] == 0.0125
        assert result.performance_analysis["average_score"] == 0.75
        assert "cost efficiency" in result.comparison_summary

    @patch('src.services.model_recommender.get_models')
    def test_model_catalog_integration(self, mock_get_models):
        """Test integration with the model catalog service."""
        from src.services.model_recommender import get_model_comparison_data

        # Mock different types of models
        mock_models = [
            MagicMock(id="openai/gpt-4", display_name="GPT-4", provider="openai",
                     input_price=0.01, output_price=0.03, description=None),
            MagicMock(id="anthropic/claude", display_name="Claude", provider="anthropic",
                     input_price=0.015, output_price=0.075, description=None),
            MagicMock(id="google/gemini", display_name="Gemini", provider="google",
                     input_price=0.001, output_price=0.002, description=None),
            MagicMock(id="meta/llama", display_name="Llama", provider="meta",
                     input_price=None, output_price=None, description=None),  # No pricing
        ]
        mock_get_models.return_value = (mock_models, "dynamic", None)

        # Test getting data for all models
        all_details = get_model_comparison_data([
            "openai/gpt-4", "anthropic/claude", "google/gemini", "meta/llama"
        ])

        assert len(all_details) == 4

        # Verify pricing calculations
        gpt4 = next(d for d in all_details if d.model_id == "openai/gpt-4")
        assert gpt4.average_cost_per_1k == 0.02  # (0.01 + 0.03) / 2

        gemini = next(d for d in all_details if d.model_id == "google/gemini")
        assert gemini.average_cost_per_1k == 0.0015  # (0.001 + 0.002) / 2

        llama = next(d for d in all_details if d.model_id == "meta/llama")
        assert llama.average_cost_per_1k is None  # No pricing available

    def test_performance_score_calculation(self):
        """Test that performance scores are calculated reasonably."""
        from src.services.model_recommender import _estimate_performance_score
        from services.catalog import ModelInfo

        # Test different provider scoring
        openai_model = ModelInfo(
            id="openai/gpt-4", display_name="GPT-4", provider="openai",
            input_price=0.01, output_price=0.03
        )
        openai_score = _estimate_performance_score(openai_model)

        anthropic_model = ModelInfo(
            id="anthropic/claude", display_name="Claude", provider="anthropic",
            input_price=0.015, output_price=0.075
        )
        anthropic_score = _estimate_performance_score(anthropic_model)

        # OpenAI should score higher than base
        assert openai_score >= 0.5
        assert anthropic_score >= 0.5

        # Test cost impact on scoring
        cheap_model = ModelInfo(
            id="cheap/model", display_name="Cheap Model", provider="unknown",
            input_price=0.001, output_price=0.001
        )
        cheap_score = _estimate_performance_score(cheap_model)

        expensive_model = ModelInfo(
            id="expensive/model", display_name="Expensive Model", provider="unknown",
            input_price=0.1, output_price=0.1
        )
        expensive_score = _estimate_performance_score(expensive_model)

        # Cheap model should score higher than expensive one
        assert cheap_score > expensive_score


if __name__ == "__main__":
    pytest.main([__file__])