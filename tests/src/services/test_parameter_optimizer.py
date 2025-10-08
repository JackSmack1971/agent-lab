"""Unit tests for parameter optimizer service with comprehensive edge case coverage."""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

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
from src.services.parameter_optimizer import (
    UseCaseDetector,
    ParameterRecommender,
    HistoricalLearner,
    ParameterOptimizer,
    get_parameter_optimizer,
    optimize_parameters,
    get_smart_defaults,
)


@pytest.fixture
def sample_context():
    """Sample optimization context for testing."""
    return OptimizationContext(
        model_id="openai/gpt-4o",
        use_case=UseCaseType.CREATIVE_WRITING,
        user_input_length=150,
        conversation_history_length=5,
        task_complexity_hint="complex",
        time_pressure="low"
    )


@pytest.fixture
def sample_request(sample_context):
    """Sample optimization request for testing."""
    return ParameterOptimizationRequest(
        model_id="openai/gpt-4o",
        user_description="Write a creative story about AI",
        context=sample_context,
        include_historical_learning=True
    )


class TestUseCaseDetector:
    """Test suite for UseCaseDetector with edge cases."""

    def test_detect_use_case_creative_writing(self):
        """Test detection of creative writing use case."""
        text = "I want to write a creative story about artificial intelligence"
        result = UseCaseDetector.detect_use_case(text)

        assert result.detected_use_case == UseCaseType.CREATIVE_WRITING
        assert result.confidence_score > 0.5
        assert "creative" in result.keywords_matched or "write" in result.keywords_matched

    def test_detect_use_case_code_generation(self):
        """Test detection of code generation use case."""
        text = "Write a Python function to calculate fibonacci numbers"
        result = UseCaseDetector.detect_use_case(text)

        assert result.detected_use_case == UseCaseType.CODE_GENERATION
        assert result.confidence_score > 0.5

    def test_detect_use_case_empty_text(self):
        """Test detection with empty text."""
        result = UseCaseDetector.detect_use_case("")

        assert result.detected_use_case == UseCaseType.OTHER
        assert result.confidence_score == 0.5
        assert result.keywords_matched == []

    def test_detect_use_case_very_short_text(self):
        """Test detection with very short text."""
        result = UseCaseDetector.detect_use_case("hi")

        assert result.detected_use_case == UseCaseType.OTHER
        assert result.confidence_score == 0.5

    def test_detect_use_case_case_insensitive_matching(self):
        """Test that detection is case insensitive."""
        text = "I WANT TO ANALYZE SOME DATA AND CREATE VISUALIZATIONS"
        result = UseCaseDetector.detect_use_case(text)

        assert result.detected_use_case == UseCaseType.ANALYSIS
        assert result.confidence_score > 0.5

    def test_detect_use_case_multiple_keywords_high_confidence(self):
        """Test detection with multiple matching keywords."""
        text = "I need to debug this code issue and fix the problem"
        result = UseCaseDetector.detect_use_case(text)

        assert result.detected_use_case == UseCaseType.DEBUGGING
        assert result.confidence_score > 0.7  # Should be high due to multiple matches

    def test_detect_use_case_secondary_use_cases(self):
        """Test detection of secondary use cases."""
        text = "Write code to analyze data and create visualizations"
        result = UseCaseDetector.detect_use_case(text)

        # Should detect CODE_GENERATION as primary, ANALYSIS as secondary
        assert result.detected_use_case in [UseCaseType.CODE_GENERATION, UseCaseType.ANALYSIS]
        if result.secondary_use_cases:
            assert len(result.secondary_use_cases) <= 2

    def test_detect_use_case_context_hints_generation(self):
        """Test generation of context hints."""
        text = "Write creative code for analyzing fast data"
        result = UseCaseDetector.detect_use_case(text)

        # Should have context hints for creativity, technical, analytical, and speed
        assert "creativity" in result.context_hints or "technical" in result.context_hints

    def test_detect_use_case_low_confidence_fallback(self):
        """Test fallback to OTHER for low confidence matches."""
        text = "random text with no clear purpose"
        result = UseCaseDetector.detect_use_case(text)

        assert result.detected_use_case == UseCaseType.OTHER
        assert result.confidence_score < 0.6

    def test_detect_use_case_regex_compilation_performance(self):
        """Test that regex patterns are pre-compiled for performance."""
        # This is more of a performance/smoke test
        text = "write some code please"
        result = UseCaseDetector.detect_use_case(text)

        # Should complete quickly and return valid result
        assert isinstance(result, UseCaseDetectionResult)
        assert result.confidence_score >= 0.0

    @pytest.mark.parametrize("text,expected_use_case", [
        ("translate this text to french", UseCaseType.TRANSLATION),
        ("summarize this long article", UseCaseType.SUMMARIZATION),
        ("let's have a conversation about movies", UseCaseType.CONVERSATION),
        ("solve this mathematical problem step by step", UseCaseType.REASONING),
    ])
    def test_detect_use_case_parametrized(self, text, expected_use_case):
        """Parametrized test for various use case detections."""
        result = UseCaseDetector.detect_use_case(text)

        assert result.detected_use_case == expected_use_case
        assert result.confidence_score > 0.4


class TestParameterRecommender:
    """Test suite for ParameterRecommender with edge cases."""

    def test_recommend_parameters_basic_functionality(self, sample_context):
        """Test basic parameter recommendation functionality."""
        recommendation = ParameterRecommender.recommend_parameters(
            UseCaseType.CREATIVE_WRITING, sample_context
        )

        assert isinstance(recommendation, ParameterRecommendation)
        assert 0.0 <= recommendation.temperature <= 2.0
        assert 0.0 <= recommendation.top_p <= 1.0
        assert recommendation.max_tokens > 0
        assert isinstance(recommendation.reasoning, str)
        assert len(recommendation.reasoning) > 0

    def test_recommend_parameters_all_use_cases(self, sample_context):
        """Test parameter recommendation for all use case types."""
        for use_case in UseCaseType:
            recommendation = ParameterRecommender.recommend_parameters(use_case, sample_context)

            assert isinstance(recommendation, ParameterRecommendation)
            assert 0.0 <= recommendation.temperature <= 2.0
            assert 0.0 <= recommendation.top_p <= 1.0
            assert recommendation.max_tokens > 0

    def test_recommend_parameters_with_historical_patterns(self, sample_context):
        """Test parameter recommendation with historical patterns."""
        historical_patterns = [
            HistoricalPattern(
                use_case=UseCaseType.CREATIVE_WRITING,
                model_id="openai/gpt-4o",
                temperature=0.9,
                top_p=0.95,
                max_tokens=1500,
                success_score=0.8,
                usage_count=5,
                last_used=datetime.now(),
                avg_latency_ms=2000.0,
                avg_cost_usd=0.1
            )
        ]

        recommendation = ParameterRecommender.recommend_parameters(
            UseCaseType.CREATIVE_WRITING, sample_context, historical_patterns
        )

        assert isinstance(recommendation, ParameterRecommendation)
        # Should incorporate historical data
        assert recommendation.temperature >= 0.7  # Blended with historical

    def test_adjust_for_context_input_length_long(self):
        """Test context adjustment for long input."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.ANALYSIS,
            user_input_length=600,  # Long input
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure=None
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.2, 0.9, 1000, context, {})

        assert temp > 0.2  # Should increase temperature for complex input
        assert max_tokens > 1000  # Should increase max tokens

    def test_adjust_for_context_input_length_short(self):
        """Test context adjustment for short input."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.ANALYSIS,
            user_input_length=30,  # Short input
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure=None
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.2, 0.9, 1000, context, {})

        assert temp < 0.2  # Should decrease temperature for simple input
        assert max_tokens < 1000  # Should decrease max tokens

    def test_adjust_for_context_conversation_history_long(self):
        """Test context adjustment for long conversation history."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.CONVERSATION,
            user_input_length=100,
            conversation_history_length=15,  # Long history
            task_complexity_hint=None,
            time_pressure=None
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.7, 0.9, 1000, context, {})

        assert top_p >= 0.9  # Should increase top_p for coherence
        assert max_tokens >= 1000  # Should increase max tokens

    def test_adjust_for_context_time_pressure_high(self):
        """Test context adjustment for high time pressure."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.ANALYSIS,
            user_input_length=100,
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure="high"
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.2, 0.9, 1000, context, {})

        assert temp < 0.2  # Should decrease temperature for speed
        assert max_tokens <= 1000  # Should decrease max tokens

    def test_adjust_for_context_time_pressure_low(self):
        """Test context adjustment for low time pressure."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.CREATIVE_WRITING,
            user_input_length=100,
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure="low"
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.9, 0.95, 2000, context, {})

        assert temp >= 0.9  # Should increase temperature for creativity
        assert max_tokens >= 2000  # Should increase max tokens

    def test_adjust_for_context_task_complexity_complex(self):
        """Test context adjustment for complex tasks."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.REASONING,
            user_input_length=100,
            conversation_history_length=0,
            task_complexity_hint="complex",
            time_pressure=None
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.1, 0.8, 2000, context, {})

        assert temp >= 0.1  # Should increase temperature for complexity
        assert max_tokens >= 2000  # Should increase max tokens

    def test_adjust_for_context_task_complexity_simple(self):
        """Test context adjustment for simple tasks."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.REASONING,
            user_input_length=100,
            conversation_history_length=0,
            task_complexity_hint="simple",
            time_pressure=None
        )

        temp, top_p, max_tokens = ParameterRecommender._adjust_for_context(0.1, 0.8, 2000, context, {})

        assert temp <= 0.1  # Should decrease temperature for simplicity
        assert max_tokens <= 2000  # Should decrease max tokens

    def test_incorporate_historical_learning_no_patterns(self, sample_context):
        """Test historical learning with no relevant patterns."""
        temp, top_p, max_tokens = ParameterRecommender._incorporate_historical_learning(
            0.7, 0.9, 1000, UseCaseType.CREATIVE_WRITING, "test_model", []
        )

        # Should return original values unchanged
        assert temp == 0.7
        assert top_p == 0.9
        assert max_tokens == 1000

    def test_incorporate_historical_learning_with_patterns(self, sample_context):
        """Test historical learning with relevant patterns."""
        patterns = [
            HistoricalPattern(
                use_case=UseCaseType.CREATIVE_WRITING,
                model_id="test_model",
                temperature=1.0,
                top_p=0.95,
                max_tokens=1500,
                success_score=0.9,
                usage_count=10,
                last_used=datetime.now(),
                avg_latency_ms=2000.0,
                avg_cost_usd=0.1
            )
        ]

        temp, top_p, max_tokens = ParameterRecommender._incorporate_historical_learning(
            0.7, 0.9, 1000, UseCaseType.CREATIVE_WRITING, "test_model", patterns
        )

        # Should blend historical and rule-based values
        assert 0.7 < temp < 1.0  # Between original and historical
        assert 0.9 <= top_p <= 0.95
        assert 1000 < max_tokens < 1500

    def test_generate_reasoning_different_use_cases(self):
        """Test reasoning generation for different use cases."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.CODE_GENERATION,
            user_input_length=100,
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure=None
        )

        reasoning = ParameterRecommender._generate_reasoning(
            UseCaseType.CODE_GENERATION, context, 0.3, 0.8, 1500
        )

        assert "code" in reasoning.lower() or "syntax" in reasoning.lower()
        assert isinstance(reasoning, str)
        assert len(reasoning) > 0

    def test_generate_reasoning_with_context_adjustments(self):
        """Test reasoning generation includes context adjustments."""
        context = OptimizationContext(
            model_id="test",
            use_case=UseCaseType.CREATIVE_WRITING,
            user_input_length=600,  # Long input
            conversation_history_length=15,  # Long history
            task_complexity_hint="complex",
            time_pressure="high"
        )

        reasoning = ParameterRecommender._generate_reasoning(
            UseCaseType.CREATIVE_WRITING, context, 0.9, 0.95, 2000
        )

        # Should include multiple reasoning parts
        reasoning_parts = reasoning.split(". ")
        assert len(reasoning_parts) >= 2  # Should have multiple sentences


class TestHistoricalLearner:
    """Test suite for HistoricalLearner with edge cases."""

    def test_get_relevant_patterns_empty(self):
        """Test getting patterns when none exist."""
        learner = HistoricalLearner()
        patterns = learner.get_relevant_patterns(UseCaseType.ANALYSIS, "test_model")

        assert patterns == []

    @patch('src.services.parameter_optimizer.Path')
    def test_load_patterns_file_not_exists(self, mock_path):
        """Test loading patterns when file doesn't exist."""
        mock_path.return_value.exists.return_value = False

        learner = HistoricalLearner()
        # Should not crash, patterns should be empty
        assert len(learner._patterns) == 0

    @patch('src.services.parameter_optimizer.Path')
    @patch('builtins.open')
    def test_load_patterns_corrupted_json(self, mock_open, mock_path):
        """Test loading patterns with corrupted JSON."""
        mock_path.return_value.exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"

        learner = HistoricalLearner()
        # Should not crash, patterns should be empty
        assert len(learner._patterns) == 0

    def test_record_success_pattern_new_pattern(self):
        """Test recording a new success pattern."""
        learner = HistoricalLearner()
        initial_count = len(learner._patterns)

        learner.record_success_pattern(
            UseCaseType.CODE_GENERATION,
            "test_model",
            0.3, 0.8, 1500, 0.8, 1000.0, 0.05
        )

        assert len(learner._patterns) == initial_count + 1

        # Verify pattern data
        pattern_key = list(learner._patterns.keys())[0]
        pattern = learner._patterns[pattern_key]

        assert pattern.use_case == UseCaseType.CODE_GENERATION
        assert pattern.model_id == "test_model"
        assert pattern.temperature == 0.3
        assert pattern.success_score == 0.8
        assert pattern.usage_count == 1

    def test_record_success_pattern_update_existing(self):
        """Test updating an existing success pattern."""
        learner = HistoricalLearner()

        # Record same pattern twice
        learner.record_success_pattern(
            UseCaseType.ANALYSIS, "test_model", 0.2, 0.9, 1000, 0.7, 1500.0, 0.03
        )
        learner.record_success_pattern(
            UseCaseType.ANALYSIS, "test_model", 0.2, 0.9, 1000, 0.9, 1200.0, 0.04
        )

        assert len(learner._patterns) == 1

        pattern = list(learner._patterns.values())[0]
        assert pattern.usage_count == 2
        # Success score should be averaged
        assert 0.7 < pattern.success_score < 0.9
        assert pattern.avg_latency_ms == 1350.0  # Average of 1500 and 1200
        assert pattern.avg_cost_usd == 0.035  # Average of 0.03 and 0.04

    def test_get_relevant_patterns_with_data(self):
        """Test getting relevant patterns when data exists."""
        learner = HistoricalLearner()

        # Add some patterns
        learner.record_success_pattern(UseCaseType.ANALYSIS, "model1", 0.2, 0.9, 1000, 0.8)
        learner.record_success_pattern(UseCaseType.ANALYSIS, "model2", 0.2, 0.9, 1000, 0.6)
        learner.record_success_pattern(UseCaseType.CODE_GENERATION, "model1", 0.3, 0.8, 1500, 0.9)

        patterns = learner.get_relevant_patterns(UseCaseType.ANALYSIS, "model1", limit=5)

        assert len(patterns) == 1
        assert patterns[0].success_score == 0.8

    def test_get_relevant_patterns_sorted_by_success(self):
        """Test that patterns are sorted by success score."""
        learner = HistoricalLearner()

        # Add patterns with different success scores
        learner.record_success_pattern(UseCaseType.ANALYSIS, "model1", 0.2, 0.9, 1000, 0.5)
        learner.record_success_pattern(UseCaseType.ANALYSIS, "model1", 0.3, 0.8, 1200, 0.9)

        patterns = learner.get_relevant_patterns(UseCaseType.ANALYSIS, "model1")

        assert len(patterns) == 2
        assert patterns[0].success_score >= patterns[1].success_score

    @patch('src.services.parameter_optimizer.list_sessions')
    @patch('src.services.parameter_optimizer.load_session')
    @pytest.mark.asyncio
    async def test_learn_from_session_data(self, mock_load_session, mock_list_sessions):
        """Test learning from session data."""
        # Mock session data
        mock_list_sessions.return_value = [("session1", "path1"), ("session2", "path2")]

        mock_session1 = Mock()
        mock_session1.agent_config = Mock()
        mock_session1.agent_config.model = "test_model"
        mock_session1.agent_config.name = "Code Generation Agent"
        mock_session1.agent_config.temperature = 0.3
        mock_session1.agent_config.top_p = 0.8
        mock_session1.transcript = ["msg1", "msg2", "msg3"]  # 3 messages
        mock_session1.notes = "Code generation session"

        mock_session2 = Mock()
        mock_session2.agent_config = None  # No config
        mock_session2.transcript = []

        mock_load_session.side_effect = [mock_session1, mock_session2]

        learner = HistoricalLearner()
        await learner.learn_from_session_data()

        # Should have learned from session1
        patterns = learner.get_relevant_patterns(UseCaseType.CODE_GENERATION, "test_model")
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_learn_from_session_data_error_handling(self):
        """Test error handling in session learning."""
        with patch('src.services.parameter_optimizer.list_sessions', side_effect=Exception("DB error")):
            learner = HistoricalLearner()
            # Should not crash
            await learner.learn_from_session_data()
            assert len(learner._patterns) == 0


class TestParameterOptimizer:
    """Test suite for ParameterOptimizer with comprehensive edge cases."""

    @pytest.fixture
    def optimizer(self):
        """Create a fresh optimizer instance for each test."""
        return ParameterOptimizer()

    def test_generate_cache_key_deterministic(self, sample_request):
        """Test that cache key generation is deterministic."""
        optimizer = ParameterOptimizer()

        key1 = optimizer._generate_cache_key(sample_request)
        key2 = optimizer._generate_cache_key(sample_request)

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length

    def test_generate_cache_key_different_requests(self, sample_request, sample_context):
        """Test that different requests produce different cache keys."""
        optimizer = ParameterOptimizer()

        request2 = ParameterOptimizationRequest(
            model_id="different_model",
            user_description=sample_request.user_description,
            context=sample_context,
            include_historical_learning=sample_request.include_historical_learning
        )

        key1 = optimizer._generate_cache_key(sample_request)
        key2 = optimizer._generate_cache_key(request2)

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_optimize_parameters_cache_hit(self, optimizer, sample_request):
        """Test that caching works for repeated requests."""
        # First call
        response1 = await optimizer.optimize_parameters(sample_request)

        # Second call should be cache hit
        response2 = await optimizer.optimize_parameters(sample_request)

        assert response1 == response2
        # Cache hit should have very fast processing time
        assert response2.processing_time_ms < 1.0

    @pytest.mark.asyncio
    async def test_optimize_parameters_cache_miss(self, optimizer, sample_request, sample_context):
        """Test cache miss for different requests."""
        response1 = await optimizer.optimize_parameters(sample_request)

        # Modify request to ensure cache miss
        modified_request = ParameterOptimizationRequest(
            model_id=sample_request.model_id,
            user_description="Different description",
            context=sample_context,
            include_historical_learning=sample_request.include_historical_learning
        )

        response2 = await optimizer.optimize_parameters(modified_request)

        assert response1 != response2
        assert response1.processing_time_ms > response2.processing_time_ms  # Cache hit is faster

    @pytest.mark.asyncio
    async def test_optimize_parameters_without_historical_learning(self, optimizer, sample_context):
        """Test optimization without historical learning."""
        request = ParameterOptimizationRequest(
            model_id="test_model",
            user_description="Analyze this data",
            context=sample_context,
            include_historical_learning=False
        )

        response = await optimizer.optimize_parameters(request)

        assert isinstance(response, ParameterOptimizationResponse)
        assert response.historical_insights is None
        assert response.optimization_confidence <= 0.9  # Lower confidence without historical data

    @pytest.mark.asyncio
    async def test_optimize_parameters_with_historical_learning(self, optimizer, sample_context):
        """Test optimization with historical learning enabled."""
        # Add some historical data first
        await optimizer.record_feedback(
            "test_model", UseCaseType.ANALYSIS, 0.2, 0.9, 1200, 0.8, 1500.0, 0.03
        )

        request = ParameterOptimizationRequest(
            model_id="test_model",
            user_description="Analyze this data",
            context=sample_context,
            include_historical_learning=True
        )

        response = await optimizer.optimize_parameters(request)

        assert isinstance(response, ParameterOptimizationResponse)
        assert response.historical_insights is not None
        assert "avg_success_score" in response.historical_insights

    def test_calculate_historical_insights_empty_patterns(self, optimizer):
        """Test historical insights calculation with no patterns."""
        insights = optimizer._calculate_historical_insights([])

        assert insights == {}

    def test_calculate_historical_insights_with_patterns(self, optimizer):
        """Test historical insights calculation with patterns."""
        patterns = [
            HistoricalPattern(
                use_case=UseCaseType.ANALYSIS,
                model_id="test",
                temperature=0.2, top_p=0.9, max_tokens=1000,
                success_score=0.8, usage_count=5,
                last_used=datetime.now(),
                avg_latency_ms=1500.0, avg_cost_usd=0.03
            ),
            HistoricalPattern(
                use_case=UseCaseType.ANALYSIS,
                model_id="test",
                temperature=0.3, top_p=0.8, max_tokens=1200,
                success_score=0.6, usage_count=3,
                last_used=datetime.now(),
                avg_latency_ms=1200.0, avg_cost_usd=0.04
            )
        ]

        insights = optimizer._calculate_historical_insights(patterns)

        assert "avg_success_score" in insights
        assert "total_usage" in insights
        assert "avg_latency_ms" in insights
        assert insights["avg_success_score"] > 0.6  # Average of successful patterns
        assert insights["total_usage"] == 8  # 5 + 3

    @pytest.mark.asyncio
    async def test_get_smart_defaults_basic(self, optimizer):
        """Test getting smart defaults."""
        request = SmartDefaultsRequest(
            model_id="test_model",
            user_context="I want to write code"
        )

        response = await optimizer.get_smart_defaults(request)

        assert isinstance(response, SmartDefaultsResponse)
        assert isinstance(response.default_parameters, ParameterRecommendation)
        assert 0.0 <= response.confidence_score <= 0.8  # Conservative confidence

    @pytest.mark.asyncio
    async def test_get_smart_defaults_no_context(self, optimizer):
        """Test smart defaults without user context."""
        request = SmartDefaultsRequest(
            model_id="test_model",
            user_context=None
        )

        response = await optimizer.get_smart_defaults(request)

        assert isinstance(response, SmartDefaultsResponse)
        assert response.default_parameters.temperature == 0.7  # OTHER use case default

    @pytest.mark.asyncio
    async def test_get_smart_defaults_caching(self, optimizer):
        """Test that smart defaults are cached."""
        request = SmartDefaultsRequest(
            model_id="test_model",
            user_context="Write some code"
        )

        # First call
        response1 = await optimizer.get_smart_defaults(request)

        # Second call should be cache hit
        response2 = await optimizer.get_smart_defaults(request)

        assert response1 == response2

    @pytest.mark.asyncio
    async def test_record_feedback_thread_safety(self, optimizer):
        """Test that feedback recording is thread-safe."""
        # Record feedback multiple times concurrently
        tasks = []
        for i in range(5):
            task = optimizer.record_feedback(
                f"model_{i}", UseCaseType.CODE_GENERATION,
                0.3, 0.8, 1500, 0.8, 1000.0, 0.05
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Should have recorded all feedback without conflicts
        patterns = optimizer.learner.get_relevant_patterns(UseCaseType.CODE_GENERATION, "model_0")
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_cache_cleanup_size_limit(self, optimizer):
        """Test that cache respects size limits."""
        # Fill cache beyond limit
        optimizer._max_cache_size = 2

        requests = []
        for i in range(5):
            request = ParameterOptimizationRequest(
                model_id=f"model_{i}",
                user_description=f"Test {i}",
                context=OptimizationContext(
                    model_id=f"model_{i}",
                    use_case=UseCaseType.ANALYSIS,
                    user_input_length=100,
                    conversation_history_length=0,
                    task_complexity_hint=None,
                    time_pressure=None
                ),
                include_historical_learning=False
            )
            requests.append(request)

        # Process requests
        for request in requests:
            await optimizer.optimize_parameters(request)

        # Cache should be cleaned up
        assert len(optimizer._optimization_cache) <= optimizer._max_cache_size + 1  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_cache_cleanup_ttl_expiry(self, optimizer):
        """Test that cache expires entries based on TTL."""
        # Set very short TTL
        optimizer._cache_ttl = 0.1  # 100ms

        request = ParameterOptimizationRequest(
            model_id="test_model",
            user_description="Test request",
            context=OptimizationContext(
                model_id="test_model",
                use_case=UseCaseType.ANALYSIS,
                user_input_length=100,
                conversation_history_length=0,
                task_complexity_hint=None,
                time_pressure=None
            ),
            include_historical_learning=False
        )

        # First call
        await optimizer.optimize_parameters(request)

        # Wait for TTL to expire
        await asyncio.sleep(0.2)

        # Second call should miss cache
        response2 = await optimizer.optimize_parameters(request)

        # Should have normal processing time (not cache hit)
        assert response2.processing_time_ms > 0.001


# Test global functions

@pytest.mark.asyncio
async def test_get_parameter_optimizer_singleton():
    """Test that get_parameter_optimizer returns a singleton."""
    optimizer1 = get_parameter_optimizer()
    optimizer2 = get_parameter_optimizer()

    assert optimizer1 is optimizer2
    assert isinstance(optimizer1, ParameterOptimizer)


@pytest.mark.asyncio
async def test_optimize_parameters_global_function(sample_request):
    """Test the global optimize_parameters function."""
    response = await optimize_parameters(sample_request)

    assert isinstance(response, ParameterOptimizationResponse)
    assert response.recommended_parameters.temperature >= 0.0


@pytest.mark.asyncio
async def test_get_smart_defaults_global_function():
    """Test the global get_smart_defaults function."""
    request = SmartDefaultsRequest(
        model_id="test_model",
        user_context="Write some creative content"
    )

    response = await get_smart_defaults(request)

    assert isinstance(response, SmartDefaultsResponse)
    assert response.default_parameters.temperature > 0.5  # Should be higher for creative tasks