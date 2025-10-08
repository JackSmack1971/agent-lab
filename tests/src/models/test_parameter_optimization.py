"""Unit tests for parameter optimization models with comprehensive validation."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.models.parameter_optimization import (
    UseCaseType,
    UseCaseDetectionResult,
    ParameterRecommendation,
    OptimizationContext,
    HistoricalPattern,
    ParameterOptimizationRequest,
    ParameterOptimizationResponse,
    SmartDefaultsRequest,
    SmartDefaultsResponse,
)


class TestUseCaseType:
    """Test suite for UseCaseType enum."""

    def test_use_case_type_values(self):
        """Test that all expected use case types are defined."""
        expected_values = {
            "creative_writing", "code_generation", "analysis", "summarization",
            "conversation", "reasoning", "debugging", "translation", "other"
        }

        actual_values = {member.value for member in UseCaseType}
        assert actual_values == expected_values

    def test_use_case_type_string_conversion(self):
        """Test string conversion of use case types."""
        for use_case in UseCaseType:
            assert isinstance(str(use_case), str)
            assert use_case.value in str(use_case)


class TestUseCaseDetectionResult:
    """Test suite for UseCaseDetectionResult model."""

    def test_valid_creation(self):
        """Test creating a valid UseCaseDetectionResult."""
        result = UseCaseDetectionResult(
            detected_use_case=UseCaseType.CREATIVE_WRITING,
            confidence_score=0.85,
            secondary_use_cases=[UseCaseType.ANALYSIS],
            keywords_matched=["creative", "writing"],
            context_hints={"creativity": 0.9}
        )

        assert result.detected_use_case == UseCaseType.CREATIVE_WRITING
        assert result.confidence_score == 0.85
        assert result.secondary_use_cases == [UseCaseType.ANALYSIS]
        assert result.keywords_matched == ["creative", "writing"]
        assert result.context_hints == {"creativity": 0.9}

    def test_confidence_score_bounds(self):
        """Test confidence score validation bounds."""
        # Valid bounds
        UseCaseDetectionResult(
            detected_use_case=UseCaseType.ANALYSIS,
            confidence_score=0.0
        )
        UseCaseDetectionResult(
            detected_use_case=UseCaseType.ANALYSIS,
            confidence_score=1.0
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            UseCaseDetectionResult(
                detected_use_case=UseCaseType.ANALYSIS,
                confidence_score=-0.1
            )
        with pytest.raises(ValidationError):
            UseCaseDetectionResult(
                detected_use_case=UseCaseType.ANALYSIS,
                confidence_score=1.1
            )

    def test_default_values(self):
        """Test default values for optional fields."""
        result = UseCaseDetectionResult(
            detected_use_case=UseCaseType.OTHER,
            confidence_score=0.5
        )

        assert result.secondary_use_cases == []
        assert result.keywords_matched == []
        assert result.context_hints == {}

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = UseCaseDetectionResult(
            detected_use_case=UseCaseType.CODE_GENERATION,
            confidence_score=0.92,
            secondary_use_cases=[UseCaseType.DEBUGGING],
            keywords_matched=["code", "function"],
            context_hints={"technical": 0.88}
        )

        json_str = original.model_dump_json()
        restored = UseCaseDetectionResult.model_validate_json(json_str)

        assert original == restored


class TestParameterRecommendation:
    """Test suite for ParameterRecommendation model."""

    def test_valid_creation(self):
        """Test creating a valid ParameterRecommendation."""
        rec = ParameterRecommendation(
            temperature=0.8,
            top_p=0.9,
            max_tokens=1500,
            reasoning="Balanced parameters for creative tasks"
        )

        assert rec.temperature == 0.8
        assert rec.top_p == 0.9
        assert rec.max_tokens == 1500
        assert rec.reasoning == "Balanced parameters for creative tasks"

    def test_temperature_bounds(self):
        """Test temperature validation bounds."""
        # Valid bounds
        ParameterRecommendation(
            temperature=0.0,
            top_p=0.5,
            max_tokens=100,
            reasoning="test"
        )
        ParameterRecommendation(
            temperature=2.0,
            top_p=0.5,
            max_tokens=100,
            reasoning="test"
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            ParameterRecommendation(
                temperature=-0.1,
                top_p=0.5,
                max_tokens=100,
                reasoning="test"
            )
        with pytest.raises(ValidationError):
            ParameterRecommendation(
                temperature=2.1,
                top_p=0.5,
                max_tokens=100,
                reasoning="test"
            )

    def test_top_p_bounds(self):
        """Test top_p validation bounds."""
        # Valid bounds
        ParameterRecommendation(
            temperature=0.7,
            top_p=0.0,
            max_tokens=100,
            reasoning="test"
        )
        ParameterRecommendation(
            temperature=0.7,
            top_p=1.0,
            max_tokens=100,
            reasoning="test"
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            ParameterRecommendation(
                temperature=0.7,
                top_p=-0.1,
                max_tokens=100,
                reasoning="test"
            )
        with pytest.raises(ValidationError):
            ParameterRecommendation(
                temperature=0.7,
                top_p=1.1,
                max_tokens=100,
                reasoning="test"
            )

    def test_max_tokens_positive(self):
        """Test max_tokens must be positive."""
        # Valid
        ParameterRecommendation(
            temperature=0.7,
            top_p=0.5,
            max_tokens=1,
            reasoning="test"
        )
        ParameterRecommendation(
            temperature=0.7,
            top_p=0.5,
            max_tokens=100000,
            reasoning="test"
        )

        # Invalid
        with pytest.raises(ValidationError):
            ParameterRecommendation(
                temperature=0.7,
                top_p=0.5,
                max_tokens=0,
                reasoning="test"
            )
        with pytest.raises(ValidationError):
            ParameterRecommendation(
                temperature=0.7,
                top_p=0.5,
                max_tokens=-1,
                reasoning="test"
            )

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = ParameterRecommendation(
            temperature=0.75,
            top_p=0.85,
            max_tokens=2000,
            reasoning="Optimized for balanced creativity and coherence"
        )

        json_str = original.model_dump_json()
        restored = ParameterRecommendation.model_validate_json(json_str)

        assert original == restored


class TestOptimizationContext:
    """Test suite for OptimizationContext model."""

    def test_valid_creation(self):
        """Test creating a valid OptimizationContext."""
        context = OptimizationContext(
            model_id="openai/gpt-4o",
            use_case=UseCaseType.ANALYSIS,
            user_input_length=250,
            conversation_history_length=8,
            task_complexity_hint="complex",
            time_pressure="medium"
        )

        assert context.model_id == "openai/gpt-4o"
        assert context.use_case == UseCaseType.ANALYSIS
        assert context.user_input_length == 250
        assert context.conversation_history_length == 8
        assert context.task_complexity_hint == "complex"
        assert context.time_pressure == "medium"

    def test_default_values(self):
        """Test default values for optional fields."""
        context = OptimizationContext(
            model_id="test_model",
            use_case=UseCaseType.OTHER
        )

        assert context.user_input_length == 0
        assert context.conversation_history_length == 0
        assert context.task_complexity_hint is None
        assert context.time_pressure is None

    def test_time_pressure_validation(self):
        """Test time_pressure literal validation."""
        # Valid values
        for pressure in ["low", "medium", "high"]:
            context = OptimizationContext(
                model_id="test",
                use_case=UseCaseType.OTHER,
                time_pressure=pressure
            )
            assert context.time_pressure == pressure

        # Invalid value
        with pytest.raises(ValidationError):
            OptimizationContext(
                model_id="test",
                use_case=UseCaseType.OTHER,
                time_pressure="urgent"  # Not in literal
            )

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = OptimizationContext(
            model_id="anthropic/claude-3",
            use_case=UseCaseType.CODE_GENERATION,
            user_input_length=500,
            conversation_history_length=12,
            task_complexity_hint="simple",
            time_pressure="high"
        )

        json_str = original.model_dump_json()
        restored = OptimizationContext.model_validate_json(json_str)

        assert original == restored


class TestHistoricalPattern:
    """Test suite for HistoricalPattern model."""

    def test_valid_creation(self):
        """Test creating a valid HistoricalPattern."""
        pattern = HistoricalPattern(
            use_case=UseCaseType.REASONING,
            model_id="openai/gpt-4o",
            temperature=0.1,
            top_p=0.8,
            max_tokens=3000,
            success_score=0.85,
            usage_count=5,
            last_used=datetime(2024, 1, 15, 10, 30),
            avg_latency_ms=2500.0,
            avg_cost_usd=0.12
        )

        assert pattern.use_case == UseCaseType.REASONING
        assert pattern.model_id == "openai/gpt-4o"
        assert pattern.temperature == 0.1
        assert pattern.success_score == 0.85
        assert pattern.usage_count == 5

    def test_success_score_bounds(self):
        """Test success_score validation bounds."""
        # Valid bounds
        HistoricalPattern(
            use_case=UseCaseType.OTHER,
            model_id="test",
            temperature=0.5,
            top_p=0.8,
            max_tokens=1000,
            success_score=0.0
        )
        HistoricalPattern(
            use_case=UseCaseType.OTHER,
            model_id="test",
            temperature=0.5,
            top_p=0.8,
            max_tokens=1000,
            success_score=1.0
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            HistoricalPattern(
                use_case=UseCaseType.OTHER,
                model_id="test",
                temperature=0.5,
                top_p=0.8,
                max_tokens=1000,
                success_score=-0.1
            )
        with pytest.raises(ValidationError):
            HistoricalPattern(
                use_case=UseCaseType.OTHER,
                model_id="test",
                temperature=0.5,
                top_p=0.8,
                max_tokens=1000,
                success_score=1.1
            )

    def test_default_values(self):
        """Test default values for optional fields."""
        now = datetime.now()
        pattern = HistoricalPattern(
            use_case=UseCaseType.CONVERSATION,
            model_id="test_model",
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            success_score=0.8
        )

        assert pattern.usage_count == 1
        assert abs((pattern.last_used - now).total_seconds()) < 1  # Within 1 second
        assert pattern.avg_latency_ms == 0.0
        assert pattern.avg_cost_usd == 0.0

    def test_serialization_with_datetime(self):
        """Test JSON serialization with datetime fields."""
        original = HistoricalPattern(
            use_case=UseCaseType.DEBUGGING,
            model_id="test_model",
            temperature=0.05,
            top_p=0.85,
            max_tokens=1500,
            success_score=0.75,
            usage_count=3,
            last_used=datetime(2024, 3, 10, 14, 25, 30),
            avg_latency_ms=1800.5,
            avg_cost_usd=0.08
        )

        json_str = original.model_dump_json()
        restored = HistoricalPattern.model_validate_json(json_str)

        assert original == restored
        assert original.last_used == restored.last_used


class TestParameterOptimizationRequest:
    """Test suite for ParameterOptimizationRequest model."""

    def test_valid_creation(self):
        """Test creating a valid ParameterOptimizationRequest."""
        context = OptimizationContext(
            model_id="test_model",
            use_case=UseCaseType.SUMMARIZATION
        )

        request = ParameterOptimizationRequest(
            model_id="test_model",
            user_description="Summarize this long article",
            context=context,
            include_historical_learning=True
        )

        assert request.model_id == "test_model"
        assert request.user_description == "Summarize this long article"
        assert request.context == context
        assert request.include_historical_learning is True

    def test_default_historical_learning(self):
        """Test default value for include_historical_learning."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.OTHER
        )

        request = ParameterOptimizationRequest(
            model_id="test",
            user_description="test",
            context=context
        )

        assert request.include_historical_learning is True

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        context = OptimizationContext(
            model_id="openai/gpt-4",
            use_case=UseCaseType.TRANSLATION,
            user_input_length=100,
            conversation_history_length=2
        )

        original = ParameterOptimizationRequest(
            model_id="openai/gpt-4",
            user_description="Translate this text to Spanish",
            context=context,
            include_historical_learning=False
        )

        json_str = original.model_dump_json()
        restored = ParameterOptimizationRequest.model_validate_json(json_str)

        assert original == restored


class TestParameterOptimizationResponse:
    """Test suite for ParameterOptimizationResponse model."""

    def test_valid_creation(self):
        """Test creating a valid ParameterOptimizationResponse."""
        recommendation = ParameterRecommendation(
            temperature=0.8,
            top_p=0.9,
            max_tokens=1200,
            reasoning="Balanced parameters"
        )

        detection = UseCaseDetectionResult(
            detected_use_case=UseCaseType.CONVERSATION,
            confidence_score=0.88
        )

        response = ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=detection,
            historical_insights={"success_rate": 0.82},
            optimization_confidence=0.85,
            processing_time_ms=125.5
        )

        assert response.recommended_parameters == recommendation
        assert response.use_case_detection == detection
        assert response.historical_insights == {"success_rate": 0.82}
        assert response.optimization_confidence == 0.85
        assert response.processing_time_ms == 125.5

    def test_optimization_confidence_bounds(self):
        """Test optimization_confidence validation bounds."""
        recommendation = ParameterRecommendation(
            temperature=0.7,
            top_p=0.8,
            max_tokens=1000,
            reasoning="test"
        )
        detection = UseCaseDetectionResult(
            detected_use_case=UseCaseType.OTHER,
            confidence_score=0.5
        )

        # Valid bounds
        ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=detection,
            optimization_confidence=0.0,
            processing_time_ms=100.0
        )
        ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=detection,
            optimization_confidence=1.0,
            processing_time_ms=100.0
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            ParameterOptimizationResponse(
                recommended_parameters=recommendation,
                use_case_detection=detection,
                optimization_confidence=-0.1,
                processing_time_ms=100.0
            )
        with pytest.raises(ValidationError):
            ParameterOptimizationResponse(
                recommended_parameters=recommendation,
                use_case_detection=detection,
                optimization_confidence=1.1,
                processing_time_ms=100.0
            )

    def test_optional_historical_insights(self):
        """Test that historical_insights can be None."""
        recommendation = ParameterRecommendation(
            temperature=0.7,
            top_p=0.8,
            max_tokens=1000,
            reasoning="test"
        )
        detection = UseCaseDetectionResult(
            detected_use_case=UseCaseType.OTHER,
            confidence_score=0.5
        )

        response = ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=detection,
            historical_insights=None,
            optimization_confidence=0.8,
            processing_time_ms=50.0
        )

        assert response.historical_insights is None

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        recommendation = ParameterRecommendation(
            temperature=0.65,
            top_p=0.85,
            max_tokens=1800,
            reasoning="Optimized for technical content"
        )

        detection = UseCaseDetectionResult(
            detected_use_case=UseCaseType.CODE_GENERATION,
            confidence_score=0.91,
            keywords_matched=["code", "function", "python"]
        )

        original = ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=detection,
            historical_insights={"avg_success": 0.78, "usage_count": 25},
            optimization_confidence=0.88,
            processing_time_ms=67.3
        )

        json_str = original.model_dump_json()
        restored = ParameterOptimizationResponse.model_validate_json(json_str)

        assert original == restored


class TestSmartDefaultsRequest:
    """Test suite for SmartDefaultsRequest model."""

    def test_valid_creation(self):
        """Test creating a valid SmartDefaultsRequest."""
        request = SmartDefaultsRequest(
            model_id="anthropic/claude-3-sonnet",
            user_context="Working on creative writing project"
        )

        assert request.model_id == "anthropic/claude-3-sonnet"
        assert request.user_context == "Working on creative writing project"

    def test_optional_user_context(self):
        """Test that user_context can be None."""
        request = SmartDefaultsRequest(
            model_id="test_model",
            user_context=None
        )

        assert request.user_context is None

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = SmartDefaultsRequest(
            model_id="openai/gpt-3.5-turbo",
            user_context=None
        )

        json_str = original.model_dump_json()
        restored = SmartDefaultsRequest.model_validate_json(json_str)

        assert original == restored


class TestSmartDefaultsResponse:
    """Test suite for SmartDefaultsResponse model."""

    def test_valid_creation(self):
        """Test creating a valid SmartDefaultsResponse."""
        recommendation = ParameterRecommendation(
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            reasoning="Standard defaults for general use"
        )

        response = SmartDefaultsResponse(
            default_parameters=recommendation,
            reasoning="Based on general usage patterns",
            confidence_score=0.75
        )

        assert response.default_parameters == recommendation
        assert response.reasoning == "Based on general usage patterns"
        assert response.confidence_score == 0.75

    def test_confidence_score_bounds(self):
        """Test confidence_score validation bounds."""
        recommendation = ParameterRecommendation(
            temperature=0.7,
            top_p=0.8,
            max_tokens=1000,
            reasoning="test"
        )

        # Valid bounds
        SmartDefaultsResponse(
            default_parameters=recommendation,
            reasoning="test",
            confidence_score=0.0
        )
        SmartDefaultsResponse(
            default_parameters=recommendation,
            reasoning="test",
            confidence_score=1.0
        )

        # Invalid bounds
        with pytest.raises(ValidationError):
            SmartDefaultsResponse(
                default_parameters=recommendation,
                reasoning="test",
                confidence_score=-0.1
            )
        with pytest.raises(ValidationError):
            SmartDefaultsResponse(
                default_parameters=recommendation,
                reasoning="test",
                confidence_score=1.1
            )

    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        recommendation = ParameterRecommendation(
            temperature=0.8,
            top_p=0.95,
            max_tokens=2000,
            reasoning="Creative writing defaults"
        )

        original = SmartDefaultsResponse(
            default_parameters=recommendation,
            reasoning="Optimized for creative content generation",
            confidence_score=0.82
        )

        json_str = original.model_dump_json()
        restored = SmartDefaultsResponse.model_validate_json(json_str)

        assert original == restored


# Integration tests for model relationships

class TestModelIntegration:
    """Test suite for model relationships and integration."""

    def test_complete_optimization_workflow_models(self):
        """Test that all models work together in optimization workflow."""
        # Create context
        context = OptimizationContext(
            model_id="openai/gpt-4o",
            use_case=UseCaseType.CREATIVE_WRITING,
            user_input_length=200,
            conversation_history_length=3,
            task_complexity_hint="complex",
            time_pressure="low"
        )

        # Create request
        request = ParameterOptimizationRequest(
            model_id="openai/gpt-4o",
            user_description="Write a creative story about future technology",
            context=context,
            include_historical_learning=True
        )

        # Create detection result
        detection = UseCaseDetectionResult(
            detected_use_case=UseCaseType.CREATIVE_WRITING,
            confidence_score=0.89,
            secondary_use_cases=[UseCaseType.ANALYSIS],
            keywords_matched=["creative", "story", "write"],
            context_hints={"creativity": 0.92}
        )

        # Create recommendation
        recommendation = ParameterRecommendation(
            temperature=0.85,
            top_p=0.95,
            max_tokens=2500,
            reasoning="High creativity settings for story generation"
        )

        # Create historical pattern
        pattern = HistoricalPattern(
            use_case=UseCaseType.CREATIVE_WRITING,
            model_id="openai/gpt-4o",
            temperature=0.9,
            top_p=0.95,
            max_tokens=2000,
            success_score=0.88,
            usage_count=15,
            last_used=datetime.now(),
            avg_latency_ms=3000.0,
            avg_cost_usd=0.15
        )

        # Create response
        response = ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=detection,
            historical_insights={
                "avg_success_score": 0.85,
                "total_usage": 45,
                "avg_latency_ms": 2800.0
            },
            optimization_confidence=0.91,
            processing_time_ms=42.7
        )

        # Verify all models serialize correctly together
        request_json = request.model_dump_json()
        response_json = response.model_dump_json()
        pattern_json = pattern.model_dump_json()

        # Restore and verify
        restored_request = ParameterOptimizationRequest.model_validate_json(request_json)
        restored_response = ParameterOptimizationResponse.model_validate_json(response_json)
        restored_pattern = HistoricalPattern.model_validate_json(pattern_json)

        assert restored_request == request
        assert restored_response == response
        assert restored_pattern == pattern

    def test_smart_defaults_workflow_models(self):
        """Test that smart defaults models work together."""
        # Create request
        request = SmartDefaultsRequest(
            model_id="anthropic/claude-3",
            user_context="Debugging Python code issues"
        )

        # Create recommendation
        recommendation = ParameterRecommendation(
            temperature=0.1,
            top_p=0.9,
            max_tokens=1500,
            reasoning="Low temperature for precise debugging responses"
        )

        # Create response
        response = SmartDefaultsResponse(
            default_parameters=recommendation,
            reasoning="Optimized for code debugging and error analysis",
            confidence_score=0.78
        )

        # Verify serialization
        request_json = request.model_dump_json()
        response_json = response.model_dump_json()

        restored_request = SmartDefaultsRequest.model_validate_json(request_json)
        restored_response = SmartDefaultsResponse.model_validate_json(response_json)

        assert restored_request == request
        assert restored_response == response

    def test_edge_case_serialization(self):
        """Test serialization with edge case values."""
        # Test with extreme but valid values
        detection = UseCaseDetectionResult(
            detected_use_case=UseCaseType.OTHER,
            confidence_score=0.0,  # Minimum
            secondary_use_cases=[],  # Empty list
            keywords_matched=[],  # Empty list
            context_hints={}  # Empty dict
        )

        recommendation = ParameterRecommendation(
            temperature=0.0,  # Minimum
            top_p=0.0,  # Minimum
            max_tokens=1,  # Minimum
            reasoning=""  # Empty string (but required, so this should fail)
        )

        # This should work
        json_str = detection.model_dump_json()
        restored = UseCaseDetectionResult.model_validate_json(json_str)
        assert restored == detection

        # Test maximum values
        detection_max = UseCaseDetectionResult(
            detected_use_case=UseCaseType.OTHER,
            confidence_score=1.0,  # Maximum
        )

        recommendation_max = ParameterRecommendation(
            temperature=2.0,  # Maximum
            top_p=1.0,  # Maximum
            max_tokens=100000,  # Large but valid
            reasoning="Maximum valid values"
        )

        json_str = detection_max.model_dump_json()
        restored = UseCaseDetectionResult.model_validate_json(json_str)
        assert restored == detection_max

        json_str = recommendation_max.model_dump_json()
        restored = ParameterRecommendation.model_validate_json(json_str)
        assert restored == recommendation_max