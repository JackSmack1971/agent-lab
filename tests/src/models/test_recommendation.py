"""Unit tests for recommendation models with comprehensive validation."""

import pytest
from pydantic import ValidationError

from src.models.recommendation import (
    UseCaseInput,
    SuggestedConfig,
    ModelRecommendation,
    RecommendationResponse,
)


class TestUseCaseInput:
    """Test suite for UseCaseInput model."""

    def test_valid_creation(self):
        """Test creating a valid UseCaseInput."""
        input_data = UseCaseInput(
            description="Build a chatbot for customer support",
            max_cost=0.01,
            min_speed=50.0,
            context_length_required=4096
        )

        assert input_data.description == "Build a chatbot for customer support"
        assert input_data.max_cost == 0.01
        assert input_data.min_speed == 50.0
        assert input_data.context_length_required == 4096

    def test_optional_fields_none(self):
        """Test that optional fields can be None."""
        input_data = UseCaseInput(
            description="Simple use case"
        )

        assert input_data.max_cost is None
        assert input_data.min_speed is None
        assert input_data.context_length_required is None

    def test_description_required(self):
        """Test that description is required."""
        with pytest.raises(ValidationError):
            UseCaseInput(
                max_cost=0.01  # Missing description
            )

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = UseCaseInput(
            description="Analyze large datasets efficiently",
            max_cost=0.05,
            min_speed=100.0,
            context_length_required=8192
        )

        json_str = original.model_dump_json()
        restored = UseCaseInput.model_validate_json(json_str)

        assert original == restored


class TestSuggestedConfig:
    """Test suite for SuggestedConfig model."""

    def test_valid_creation(self):
        """Test creating a valid SuggestedConfig."""
        config = SuggestedConfig(
            temperature=0.7,
            top_p=0.9,
            max_tokens=1500
        )

        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.max_tokens == 1500

    def test_temperature_bounds(self):
        """Test temperature validation bounds."""
        # Valid bounds
        SuggestedConfig(temperature=0.0, top_p=0.5, max_tokens=100)
        SuggestedConfig(temperature=2.0, top_p=0.5, max_tokens=100)

        # Invalid bounds
        with pytest.raises(ValidationError):
            SuggestedConfig(temperature=-0.1, top_p=0.5, max_tokens=100)
        with pytest.raises(ValidationError):
            SuggestedConfig(temperature=2.1, top_p=0.5, max_tokens=100)

    def test_top_p_bounds(self):
        """Test top_p validation bounds."""
        # Valid bounds
        SuggestedConfig(temperature=0.7, top_p=0.0, max_tokens=100)
        SuggestedConfig(temperature=0.7, top_p=1.0, max_tokens=100)

        # Invalid bounds
        with pytest.raises(ValidationError):
            SuggestedConfig(temperature=0.7, top_p=-0.1, max_tokens=100)
        with pytest.raises(ValidationError):
            SuggestedConfig(temperature=0.7, top_p=1.1, max_tokens=100)

    def test_max_tokens_positive(self):
        """Test max_tokens must be positive."""
        # Valid
        SuggestedConfig(temperature=0.7, top_p=0.5, max_tokens=1)

        # Invalid
        with pytest.raises(ValidationError):
            SuggestedConfig(temperature=0.7, top_p=0.5, max_tokens=0)
        with pytest.raises(ValidationError):
            SuggestedConfig(temperature=0.7, top_p=0.5, max_tokens=-1)

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = SuggestedConfig(
            temperature=0.8,
            top_p=0.95,
            max_tokens=2000
        )

        json_str = original.model_dump_json()
        restored = SuggestedConfig.model_validate_json(json_str)

        assert original == restored


class TestModelRecommendation:
    """Test suite for ModelRecommendation model."""

    def test_valid_creation(self):
        """Test creating a valid ModelRecommendation."""
        config = SuggestedConfig(
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000
        )

        recommendation = ModelRecommendation(
            model_id="openai/gpt-3.5-turbo",
            reasoning="Excellent balance of speed and cost for chat applications",
            confidence_score=0.92,
            suggested_config=config,
            estimated_cost_per_1k=0.002
        )

        assert recommendation.model_id == "openai/gpt-3.5-turbo"
        assert recommendation.reasoning == "Excellent balance of speed and cost for chat applications"
        assert recommendation.confidence_score == 0.92
        assert recommendation.suggested_config == config
        assert recommendation.estimated_cost_per_1k == 0.002

    def test_confidence_score_bounds(self):
        """Test confidence_score validation bounds."""
        config = SuggestedConfig(temperature=0.7, top_p=0.8, max_tokens=1000)

        # Valid bounds
        ModelRecommendation(
            model_id="test",
            reasoning="test",
            confidence_score=0.0,
            suggested_config=config,
            estimated_cost_per_1k=0.01
        )
        ModelRecommendation(
            model_id="test",
            reasoning="test",
            confidence_score=1.0,
            suggested_config=config,
            estimated_cost_per_1k=0.01
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            ModelRecommendation(
                model_id="test",
                reasoning="test",
                confidence_score=-0.1,
                suggested_config=config,
                estimated_cost_per_1k=0.01
            )
        with pytest.raises(ValidationError):
            ModelRecommendation(
                model_id="test",
                reasoning="test",
                confidence_score=1.1,
                suggested_config=config,
                estimated_cost_per_1k=0.01
            )

    def test_estimated_cost_non_negative(self):
        """Test estimated_cost_per_1k must be non-negative."""
        config = SuggestedConfig(temperature=0.7, top_p=0.8, max_tokens=1000)

        # Valid
        ModelRecommendation(
            model_id="test",
            reasoning="test",
            confidence_score=0.8,
            suggested_config=config,
            estimated_cost_per_1k=0.0
        )
        ModelRecommendation(
            model_id="test",
            reasoning="test",
            confidence_score=0.8,
            suggested_config=config,
            estimated_cost_per_1k=10.0
        )

        # Invalid
        with pytest.raises(ValidationError):
            ModelRecommendation(
                model_id="test",
                reasoning="test",
                confidence_score=0.8,
                suggested_config=config,
                estimated_cost_per_1k=-0.01
            )

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        config = SuggestedConfig(
            temperature=0.6,
            top_p=0.85,
            max_tokens=1200
        )

        original = ModelRecommendation(
            model_id="anthropic/claude-3-haiku",
            reasoning="Fast and cost-effective for simple tasks",
            confidence_score=0.87,
            suggested_config=config,
            estimated_cost_per_1k=0.00025
        )

        json_str = original.model_dump_json()
        restored = ModelRecommendation.model_validate_json(json_str)

        assert original == restored


class TestRecommendationResponse:
    """Test suite for RecommendationResponse model."""

    def test_valid_creation(self):
        """Test creating a valid RecommendationResponse."""
        config1 = SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000)
        config2 = SuggestedConfig(temperature=0.8, top_p=0.95, max_tokens=1500)

        rec1 = ModelRecommendation(
            model_id="openai/gpt-3.5-turbo",
            reasoning="Best speed/cost ratio",
            confidence_score=0.95,
            suggested_config=config1,
            estimated_cost_per_1k=0.002
        )

        rec2 = ModelRecommendation(
            model_id="openai/gpt-4o-mini",
            reasoning="Better quality for complex tasks",
            confidence_score=0.88,
            suggested_config=config2,
            estimated_cost_per_1k=0.00015
        )

        response = RecommendationResponse(
            recommendations=[rec1, rec2],
            analysis_summary="Two models recommended based on speed and quality requirements"
        )

        assert len(response.recommendations) == 2
        assert response.recommendations[0] == rec1
        assert response.recommendations[1] == rec2
        assert response.analysis_summary == "Two models recommended based on speed and quality requirements"

    def test_empty_recommendations_list(self):
        """Test that recommendations list cannot be empty."""
        with pytest.raises(ValidationError):
            RecommendationResponse(
                recommendations=[],  # Empty list should fail
                analysis_summary="No recommendations available"
            )

    def test_single_recommendation(self):
        """Test response with single recommendation."""
        config = SuggestedConfig(temperature=0.7, top_p=0.9, max_tokens=1000)

        rec = ModelRecommendation(
            model_id="test_model",
            reasoning="Only option available",
            confidence_score=0.75,
            suggested_config=config,
            estimated_cost_per_1k=0.005
        )

        response = RecommendationResponse(
            recommendations=[rec],
            analysis_summary="Single model recommendation"
        )

        assert len(response.recommendations) == 1
        assert response.recommendations[0] == rec

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        config = SuggestedConfig(
            temperature=0.5,
            top_p=0.8,
            max_tokens=800
        )

        rec = ModelRecommendation(
            model_id="meta-llama/llama-3-8b",
            reasoning="Good performance for analysis tasks",
            confidence_score=0.82,
            suggested_config=config,
            estimated_cost_per_1k=0.0008
        )

        original = RecommendationResponse(
            recommendations=[rec],
            analysis_summary="Recommended for analytical workloads requiring good performance"
        )

        json_str = original.model_dump_json()
        restored = RecommendationResponse.model_validate_json(json_str)

        assert original == restored


# Integration tests for model relationships

class TestRecommendationModelIntegration:
    """Test suite for recommendation model relationships and integration."""

    def test_complete_recommendation_workflow(self):
        """Test that all recommendation models work together."""
        # Create input
        input_data = UseCaseInput(
            description="I need a fast model for real-time chat translation",
            max_cost=0.005,
            min_speed=80.0,
            context_length_required=4096
        )

        # Create multiple configurations
        configs = [
            SuggestedConfig(temperature=0.3, top_p=0.9, max_tokens=500),
            SuggestedConfig(temperature=0.7, top_p=0.95, max_tokens=1000),
            SuggestedConfig(temperature=0.1, top_p=0.8, max_tokens=300)
        ]

        # Create recommendations
        recommendations = [
            ModelRecommendation(
                model_id="openai/gpt-3.5-turbo",
                reasoning="Fastest model meeting speed requirements",
                confidence_score=0.96,
                suggested_config=configs[0],
                estimated_cost_per_1k=0.0015
            ),
            ModelRecommendation(
                model_id="openai/gpt-4o-mini",
                reasoning="Best balance of speed and quality",
                confidence_score=0.89,
                suggested_config=configs[1],
                estimated_cost_per_1k=0.00015
            ),
            ModelRecommendation(
                model_id="anthropic/claude-3-haiku",
                reasoning="Excellent quality but slower",
                confidence_score=0.78,
                suggested_config=configs[2],
                estimated_cost_per_1k=0.00025
            )
        ]

        # Create response
        response = RecommendationResponse(
            recommendations=recommendations,
            analysis_summary="Three models recommended based on speed, cost, and quality trade-offs"
        )

        # Verify all models serialize correctly together
        input_json = input_data.model_dump_json()
        response_json = response.model_dump_json()

        # Restore and verify
        restored_input = UseCaseInput.model_validate_json(input_json)
        restored_response = RecommendationResponse.model_validate_json(response_json)

        assert restored_input == input_data
        assert restored_response == response
        assert len(restored_response.recommendations) == 3

        # Verify nested relationships
        for i, rec in enumerate(restored_response.recommendations):
            assert rec.suggested_config == configs[i]

    def test_edge_case_values(self):
        """Test models with edge case values."""
        # Test boundary values
        config = SuggestedConfig(
            temperature=0.0,  # Minimum
            top_p=0.0,  # Minimum
            max_tokens=1  # Minimum
        )

        recommendation = ModelRecommendation(
            model_id="test_model",
            reasoning="Minimum valid values",
            confidence_score=0.0,  # Minimum
            suggested_config=config,
            estimated_cost_per_1k=0.0  # Minimum
        )

        response = RecommendationResponse(
            recommendations=[recommendation],
            analysis_summary="Testing minimum values"
        )

        # Should serialize successfully
        json_str = response.model_dump_json()
        restored = RecommendationResponse.model_validate_json(json_str)
        assert restored == response

        # Test maximum values
        config_max = SuggestedConfig(
            temperature=2.0,  # Maximum
            top_p=1.0,  # Maximum
            max_tokens=100000  # Large but valid
        )

        recommendation_max = ModelRecommendation(
            model_id="test_model_max",
            reasoning="Maximum valid values",
            confidence_score=1.0,  # Maximum
            suggested_config=config_max,
            estimated_cost_per_1k=1000.0  # Large but valid
        )

        response_max = RecommendationResponse(
            recommendations=[recommendation_max],
            analysis_summary="Testing maximum values"
        )

        # Should serialize successfully
        json_str = response_max.model_dump_json()
        restored = RecommendationResponse.model_validate_json(json_str)
        assert restored == response_max

    def test_model_validation_errors(self):
        """Test that validation errors are properly raised."""
        # Test invalid nested config in recommendation
        invalid_config = SuggestedConfig(temperature=-0.1, top_p=0.5, max_tokens=100)  # Invalid temperature

        with pytest.raises(ValidationError):
            ModelRecommendation(
                model_id="test",
                reasoning="test",
                confidence_score=0.8,
                suggested_config=invalid_config,  # This should cause validation error
                estimated_cost_per_1k=0.01
            )

        # Test invalid confidence score
        valid_config = SuggestedConfig(temperature=0.7, top_p=0.8, max_tokens=1000)

        with pytest.raises(ValidationError):
            ModelRecommendation(
                model_id="test",
                reasoning="test",
                confidence_score=1.5,  # Invalid confidence
                suggested_config=valid_config,
                estimated_cost_per_1k=0.01
            )

        # Test empty recommendations list
        with pytest.raises(ValidationError):
            RecommendationResponse(
                recommendations=[],  # Invalid empty list
                analysis_summary="test"
            )