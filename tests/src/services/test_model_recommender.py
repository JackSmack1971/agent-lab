"""Unit tests for model recommender service."""

import pytest

from src.services.model_recommender import (
    ModelDetail,
    ModelComparisonRequest,
    ModelComparisonResult,
    compare_models,
    get_model_comparison_data,
    _calculate_average_cost,
    _estimate_performance_score,
    _create_basic_recommendations,
    _generate_comparison_summary,
)


class TestModelRecommender:
    """Test cases for model recommender service."""

    def test_calculate_average_cost(self):
        """Test average cost calculation."""
        assert _calculate_average_cost(0.01, 0.03) == 0.02
        assert _calculate_average_cost(0.005, 0.005) == 0.005
        assert _calculate_average_cost(None, 0.03) is None
        assert _calculate_average_cost(0.01, None) is None
        assert _calculate_average_cost(None, None) is None

    def test_estimate_performance_score(self):
        """Test performance score estimation."""
        from services.catalog import ModelInfo

        # OpenAI model should get high score
        openai_model = ModelInfo(
            id="openai/gpt-4",
            display_name="GPT-4",
            provider="openai",
            input_price=0.01,
            output_price=0.03,
        )
        score = _estimate_performance_score(openai_model)
        assert 0.6 <= score <= 0.8  # Base 0.5 + 0.2 for OpenAI - small cost adjustment

        # High cost model should get lower score
        expensive_model = ModelInfo(
            id="expensive/model",
            display_name="Expensive Model",
            provider="unknown",
            input_price=0.1,
            output_price=0.3,
        )
        expensive_score = _estimate_performance_score(expensive_model)
        assert expensive_score < score  # Should be lower due to high cost

def test_get_model_comparison_data(self, mock_get_models, mocker):
    get_models = mocker.patch('src.services.model_recommender.get_models')
        """Test getting model comparison data."""
        mock_models = [
            MagicMock(
                id="openai/gpt-4",
                display_name="GPT-4",
                provider="openai",
                description="Advanced model",
                input_price=0.01,
                output_price=0.03,
            ),
            MagicMock(
                id="anthropic/claude",
                display_name="Claude",
                provider="anthropic",
                description="Another model",
                input_price=0.015,
                output_price=0.075,
            ),
        ]
        mock_get_models.return_value = (mock_models, "dynamic", None)

        result = get_model_comparison_data(["openai/gpt-4", "anthropic/claude"])

        assert len(result) == 2
        assert result[0].model_id == "openai/gpt-4"
        assert result[0].display_name == "GPT-4"
        assert result[0].average_cost_per_1k == 0.02
        assert result[1].model_id == "anthropic/claude"
        assert result[1].average_cost_per_1k == 0.045

    @pytest.mark.asyncio
    async def test_compare_models(self, mock_get_data, mock_analyze):
        """Test model comparison functionality."""
        # Mock model data
        mock_model_details = [
            ModelDetail(
                model_id="openai/gpt-4",
                display_name="GPT-4",
                provider="openai",
                input_price=0.01,
                output_price=0.03,
                average_cost_per_1k=0.02,
                performance_score=0.8,
            ),
            ModelDetail(
                model_id="anthropic/claude",
                display_name="Claude",
                provider="anthropic",
                input_price=0.015,
                output_price=0.075,
                average_cost_per_1k=0.045,
                performance_score=0.75,
            ),
        ]
        mock_get_data.return_value = mock_model_details

        # Mock recommendation response
        from src.models.recommendation import ModelRecommendation, SuggestedConfig
        mock_rec_response = MagicMock()
        mock_rec_response.recommendations = [
            ModelRecommendation(
                model_id="openai/gpt-4",
                reasoning="Best for complex tasks",
                confidence_score=0.9,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.02,
            )
        ]
        mock_analyze.return_value = mock_rec_response

        # Test comparison
        request = ModelComparisonRequest(
            model_ids=["openai/gpt-4", "anthropic/claude"],
            use_case_description="Complex reasoning tasks",
            include_cost_analysis=True,
            include_performance_metrics=True,
        )

        result = await compare_models(request)

        assert isinstance(result, ModelComparisonResult)
        assert len(result.model_details) == 2
        assert len(result.recommendations) == 1
        assert "average_cost" in result.cost_analysis
        assert "average_score" in result.performance_analysis
        assert result.comparison_summary

def test_create_basic_recommendations(self, mocker):
    get_model_comparison_data = mocker.patch('src.services.model_recommender.get_model_comparison_data')
    analyze_use_case = mocker.patch('src.services.model_recommender.analyze_use_case')
        """Test basic recommendation creation."""
        model_details = [
            ModelDetail(
                model_id="openai/gpt-4",
                display_name="GPT-4",
                provider="openai",
                average_cost_per_1k=0.02,
                performance_score=0.8,
            ),
            ModelDetail(
                model_id="anthropic/claude",
                display_name="Claude",
                provider="anthropic",
                average_cost_per_1k=0.045,
                performance_score=0.75,
            ),
        ]

        recommendations = _create_basic_recommendations(model_details, "coding tasks")

        assert len(recommendations) <= 3
        assert recommendations[0].model_id == "openai/gpt-4"  # Should be first due to higher score
        assert "coding tasks" in recommendations[0].reasoning.lower()
        assert 0.4 <= recommendations[0].confidence_score <= 0.6

    def test_generate_comparison_summary(self):
        """Test comparison summary generation."""
        model_details = [
            ModelDetail(
                model_id="openai/gpt-4",
                display_name="GPT-4",
                provider="openai",
                average_cost_per_1k=0.02,
            ),
            ModelDetail(
                model_id="anthropic/claude",
                display_name="Claude",
                provider="anthropic",
                average_cost_per_1k=0.045,
            ),
        ]

        from src.models.recommendation import ModelRecommendation, SuggestedConfig
        recommendations = [
            ModelRecommendation(
                model_id="openai/gpt-4",
                reasoning="Test",
                confidence_score=0.9,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.02,
            )
        ]

        summary = _generate_comparison_summary(model_details, recommendations)

        assert "2 models" in summary
        assert "openai" in summary.lower()
        assert "anthropic" in summary.lower()
        assert "$0.0200" in summary
        assert "$0.0450" in summary

    @pytest.mark.asyncio
    async def test_compare_models_empty_list(self, mock_get_data):
        """Test comparison with empty model list."""
        mock_get_data.return_value = []

        request = ModelComparisonRequest(
            model_ids=[],
            use_case_description="test",
            include_cost_analysis=True,
            include_performance_metrics=True,
        )

        with pytest.raises(ValueError, match="No valid models found"):
            await compare_models(request)

    @pytest.mark.asyncio
    async def test_compare_models_fallback_recommendations(self, mock_create_basic, mock_get_data):
        """Test fallback to basic recommendations."""
        mock_model_details = [
            ModelDetail(
                model_id="test/model",
                display_name="Test Model",
                provider="test",
                average_cost_per_1k=0.01,
                performance_score=0.7,
            )
        ]
        mock_get_data.return_value = mock_model_details

        from src.models.recommendation import ModelRecommendation, SuggestedConfig
        mock_basic_recs = [
            ModelRecommendation(
                model_id="test/model",
                reasoning="Test reasoning",
                confidence_score=0.8,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.01,
            )
        ]
        mock_create_basic.return_value = mock_basic_recs

        # Mock analyze_use_case to return empty recommendations
        with patch('src.services.model_recommender.analyze_use_case') as mock_analyze:
            mock_response = MagicMock()
            mock_response.recommendations = []  # No matching recommendations
            mock_analyze.return_value = mock_response

            request = ModelComparisonRequest(
                model_ids=["test/model"],
                use_case_description="test use case",
                include_cost_analysis=True,
                include_performance_metrics=True,
            )

            result = await compare_models(request)

            # Should use basic recommendations
            mock_create_basic.assert_called_once()
            assert len(result.recommendations) == 1

def test_get_model_comparison_data_no_match(self, mock_get_models, mocker):
    get_models = mocker.patch('src.services.model_recommender.get_models')
    _create_basic_recommendations = mocker.patch('src.services.model_recommender._create_basic_recommendations')
    get_model_comparison_data = mocker.patch('src.services.model_recommender.get_model_comparison_data')
    get_model_comparison_data = mocker.patch('src.services.model_recommender.get_model_comparison_data')
        """Test get_model_comparison_data with no matching models to cover line 96."""
        mock_models = [
            MagicMock(id="openai/gpt-4"),
        ]
        mock_get_models.return_value = (mock_models, "dynamic", None)

        result = get_model_comparison_data(["nonexistent/model"])
        assert result == []  # No matching models

    @pytest.mark.asyncio
    async def test_compare_models_cache_hit(self, mock_analyze, mock_get_data):
        """Test compare_models with cache hit to cover lines 122-125."""
        from datetime import datetime, timezone, timedelta

        # Set up cache
        from src.services.model_recommender import _comparison_cache
        cache_key = "openai/gpt-4_Test use case_True_True"
        cached_result = MagicMock()
        cached_time = datetime.now(timezone.utc) - timedelta(minutes=30)  # Within TTL
        _comparison_cache = {cache_key: (cached_result, cached_time)}

        mock_get_data.return_value = []  # Won't be called due to cache

        request = ModelComparisonRequest(
            model_ids=["openai/gpt-4"],
            use_case_description="Test use case",
            include_cost_analysis=True,
            include_performance_metrics=True,
        )

        result = await compare_models(request)
        assert result == cached_result
        mock_get_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_compare_models_cost_analysis_no_costs(self, mock_analyze, mock_get_data):
        """Test compare_models cost analysis with no costs to cover line 158->169."""
        mock_model_details = [
            ModelDetail(
                model_id="test/model",
                display_name="Test Model",
                provider="test",
                average_cost_per_1k=None,  # No cost
                performance_score=0.8,
            )
        ]
        mock_get_data.return_value = mock_model_details

        from src.models.recommendation import ModelRecommendation, SuggestedConfig
        mock_response = MagicMock()
        mock_response.recommendations = [
            ModelRecommendation(
                model_id="test/model",
                reasoning="Test",
                confidence_score=0.8,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.01,
            )
        ]
        mock_analyze.return_value = mock_response

        request = ModelComparisonRequest(
            model_ids=["test/model"],
            use_case_description="test",
            include_cost_analysis=True,
            include_performance_metrics=False,
        )

        result = await compare_models(request)
        assert result.cost_analysis == {}  # No cost analysis due to no costs

    @pytest.mark.asyncio
    async def test_compare_models_performance_analysis_no_scores(self, mock_analyze, mock_get_data):
        """Test compare_models performance analysis with no scores to cover line 170->180."""
        mock_model_details = [
            ModelDetail(
                model_id="test/model",
                display_name="Test Model",
                provider="test",
                average_cost_per_1k=0.01,
                performance_score=None,  # No score
            )
        ]
        mock_get_data.return_value = mock_model_details

        from src.models.recommendation import ModelRecommendation, SuggestedConfig
        mock_response = MagicMock()
        mock_response.recommendations = [
            ModelRecommendation(
                model_id="test/model",
                reasoning="Test",
                confidence_score=0.8,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.01,
            )
        ]
        mock_analyze.return_value = mock_response

        request = ModelComparisonRequest(
            model_ids=["test/model"],
            use_case_description="test",
            include_cost_analysis=False,
            include_performance_metrics=True,
        )

        result = await compare_models(request)
        assert result.performance_analysis == {}  # No performance analysis due to no scores

def test_create_basic_recommendations_cost_based(self, mocker):
    analyze_use_case = mocker.patch('src.services.model_recommender.analyze_use_case')
    get_model_comparison_data = mocker.patch('src.services.model_recommender.get_model_comparison_data')
    analyze_use_case = mocker.patch('src.services.model_recommender.analyze_use_case')
    get_model_comparison_data = mocker.patch('src.services.model_recommender.get_model_comparison_data')
    analyze_use_case = mocker.patch('src.services.model_recommender.analyze_use_case')
    get_model_comparison_data = mocker.patch('src.services.model_recommender.get_model_comparison_data')
        """Test _create_basic_recommendations with cost-based reasoning to cover line 224."""
        model_details = [
            ModelDetail(
                model_id="cheap/model",
                display_name="Cheap Model",
                provider="test",
                average_cost_per_1k=0.005,  # Low cost
                performance_score=0.5,
            ),
            ModelDetail(
                model_id="expensive/model",
                display_name="Expensive Model",
                provider="test",
                average_cost_per_1k=0.1,  # High cost
                performance_score=0.5,
            ),
        ]

        recommendations = _create_basic_recommendations(model_details, "test use case")
        # First recommendation should be the cheap one due to cost efficiency
        assert recommendations[0].model_id == "cheap/model"
        assert "cost efficiency" in recommendations[0].reasoning

    def test_generate_comparison_summary_no_models(self):
        """Test _generate_comparison_summary with no models to cover line 247."""
        summary = _generate_comparison_summary([], [])
        assert summary == "No models to compare."

    def test_generate_comparison_summary_no_costs(self):
        """Test _generate_comparison_summary with no costs to cover lines 257->260."""
        model_details = [
            ModelDetail(
                model_id="test/model",
                display_name="Test Model",
                provider="test",
                average_cost_per_1k=None,  # No cost
            )
        ]

        from src.models.recommendation import ModelRecommendation, SuggestedConfig
        recommendations = [
            ModelRecommendation(
                model_id="test/model",
                reasoning="Test",
                confidence_score=0.8,
                suggested_config=SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000),
                estimated_cost_per_1k=0.01,
            )
        ]

        summary = _generate_comparison_summary(model_details, recommendations)
        assert "$" not in summary  # No cost range in summary

    def test_generate_comparison_summary_no_recommendations(self):
        """Test _generate_comparison_summary with no recommendations to cover lines 262->266."""
        model_details = [
            ModelDetail(
                model_id="test/model",
                display_name="Test Model",
                provider="test",
                average_cost_per_1k=0.01,
            )
        ]

        summary = _generate_comparison_summary(model_details, [])
        assert "top recommendation" not in summary.lower()