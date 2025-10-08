"""Integration tests for parameter optimizer with real components."""

import asyncio
import pytest
import time
from pathlib import Path

from src.services.parameter_optimizer import ParameterOptimizer, optimize_parameters, get_smart_defaults
from src.models.parameter_optimization import (
    UseCaseType,
    ParameterOptimizationRequest,
    ParameterOptimizationResponse,
    OptimizationContext,
    SmartDefaultsRequest,
    SmartDefaultsResponse,
)


class TestParameterOptimizerIntegration:
    """Integration tests for the complete parameter optimizer system."""

    @pytest.fixture
    async def optimizer(self):
        """Create a fresh optimizer for each test."""
        optimizer = ParameterOptimizer()
        # Clear any existing patterns for clean testing
        optimizer.learner._patterns.clear()
        yield optimizer

    @pytest.mark.asyncio
    async def test_end_to_end_optimization_workflow(self, optimizer):
        """Test complete optimization workflow from request to response."""
        # Create a request for creative writing
        request = ParameterOptimizationRequest(
            model_id="gpt-4",
            user_description="I want to write a creative short story about time travel",
            context=OptimizationContext(
                model_id="gpt-4",
                use_case=UseCaseType.CREATIVE_WRITING,
                user_input_length=150,
                conversation_history_length=3,
                task_complexity_hint="complex",
                time_pressure="low"
            )
        )

        # Execute optimization
        response = await optimizer.optimize_parameters(request)

        # Verify response structure
        assert response.recommended_parameters.temperature >= 0.7  # Creative writing should have higher temp
        assert response.recommended_parameters.top_p >= 0.8
        assert response.recommended_parameters.max_tokens >= 1000
        assert response.use_case_detection.detected_use_case == UseCaseType.CREATIVE_WRITING
        assert response.optimization_confidence > 0.5
        assert response.processing_time_ms < 1000  # Should be fast

        # Verify reasoning is provided
        assert len(response.recommended_parameters.reasoning) > 10

    @pytest.mark.asyncio
    async def test_learning_integration(self, optimizer):
        """Test that historical learning affects recommendations."""
        model_id = "gpt-4"
        use_case = UseCaseType.CODE_GENERATION

        # First, record some successful patterns
        await optimizer.record_feedback(
            model_id=model_id,
            use_case=use_case,
            temperature=0.2,  # Very low temperature worked well
            top_p=0.85,
            max_tokens=1200,
            success_score=0.95,
            latency_ms=1500
        )

        await optimizer.record_feedback(
            model_id=model_id,
            use_case=use_case,
            temperature=0.2,  # Same pattern, reinforce learning
            top_p=0.85,
            max_tokens=1200,
            success_score=0.92,
            latency_ms=1400
        )

        # Now make a request and see if historical learning influenced the result
        request = ParameterOptimizationRequest(
            model_id=model_id,
            user_description="Generate Python code for sorting algorithms",
            context=OptimizationContext(
                model_id=model_id,
                use_case=use_case,
                user_input_length=100,
                conversation_history_length=0,
                task_complexity_hint=None,
                time_pressure=None
            ),
            include_historical_learning=True
        )

        response = await optimizer.optimize_parameters(request)

        # The result should be influenced by historical data
        # Temperature should be closer to 0.2 than the default 0.3
        assert abs(response.recommended_parameters.temperature - 0.2) < abs(response.recommended_parameters.temperature - 0.3)

        # Should have historical insights
        assert response.historical_insights is not None
        assert "avg_success_score" in response.historical_insights

    @pytest.mark.asyncio
    async def test_smart_defaults_with_context(self, optimizer):
        """Test smart defaults adapt to user context."""
        # Test with coding context
        code_request = SmartDefaultsRequest(
            model_id="gpt-4",
            user_context="I usually write Python code and debug algorithms"
        )

        code_defaults = await optimizer.get_smart_defaults(code_request)

        # Should recommend lower temperature for coding
        assert code_defaults.default_parameters.temperature < 0.5

        # Test with creative context
        creative_request = SmartDefaultsRequest(
            model_id="gpt-4",
            user_context="I write stories and creative content"
        )

        creative_defaults = await optimizer.get_smart_defaults(creative_request)

        # Should recommend higher temperature for creative work
        assert creative_defaults.default_parameters.temperature > 0.7

        # Creative should have higher temperature than coding
        assert creative_defaults.default_parameters.temperature > code_defaults.default_parameters.temperature

    @pytest.mark.asyncio
    async def test_caching_behavior(self, optimizer):
        """Test that caching improves performance and consistency."""
        request = ParameterOptimizationRequest(
            model_id="claude-3",
            user_description="Analyze this data science problem",
            context=OptimizationContext(
                model_id="claude-3",
                use_case=UseCaseType.ANALYSIS,
                user_input_length=200,
                conversation_history_length=2,
                task_complexity_hint=None,
                time_pressure=None
            )
        )

        # First request (cache miss)
        start_time = time.time()
        response1 = await optimizer.optimize_parameters(request)
        first_request_time = (time.time() - start_time) * 1000

        # Second request (should be cached)
        start_time = time.time()
        response2 = await optimizer.optimize_parameters(request)
        second_request_time = (time.time() - start_time) * 1000

        # Cached request should be significantly faster
        assert second_request_time < first_request_time
        assert second_request_time < 10  # Should be very fast

        # Results should be identical
        assert response1.recommended_parameters.temperature == response2.recommended_parameters.temperature
        assert response1.recommended_parameters.top_p == response2.recommended_parameters.top_p
        assert response1.recommended_parameters.max_tokens == response2.recommended_parameters.max_tokens

    @pytest.mark.asyncio
    async def test_concurrent_load_simulation(self, optimizer):
        """Simulate concurrent load to test performance under stress."""
        async def worker(worker_id):
            request = ParameterOptimizationRequest(
                model_id=f"gpt-4-worker-{worker_id}",
                user_description=f"Worker {worker_id}: perform analysis task",
                context=OptimizationContext(
                    model_id=f"gpt-4-worker-{worker_id}",
                    use_case=UseCaseType.ANALYSIS,
                    user_input_length=100 + worker_id * 10,
                    conversation_history_length=worker_id % 5,
                    task_complexity_hint=None,
                    time_pressure=None
                )
            )

            start_time = time.time()
            response = await optimizer.optimize_parameters(request)
            end_time = time.time()

            return {
                'worker_id': worker_id,
                'response_time_ms': (end_time - start_time) * 1000,
                'temperature': response.recommended_parameters.temperature,
                'success': response.processing_time_ms < 2000
            }

        # Simulate 100 concurrent requests (requirement: handles 100+ concurrent)
        num_workers = 100
        tasks = [worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        response_times = [r['response_time_ms'] for r in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        success_rate = sum(1 for r in results if r['success']) / len(results)

        # Performance requirements
        assert avg_response_time < 2000, f"Average response time {avg_response_time:.1f}ms exceeds 2s requirement"
        assert max_response_time < 2000, f"Max response time {max_response_time:.1f}ms exceeds 2s requirement"
        assert success_rate > 0.99, f"Success rate {success_rate:.1%} below 99% requirement"

        # Verify results are reasonable
        temperatures = [r['temperature'] for r in results]
        assert all(0.0 <= t <= 2.0 for t in temperatures), "Temperature values out of valid range"

        print(f"Concurrent load test results:")
        print(f"  Workers: {num_workers}")
        print(f"  Avg response time: {avg_response_time:.1f}ms")
        print(f"  Max response time: {max_response_time:.1f}ms")
        print(f"  Min response time: {min_response_time:.1f}ms")
        print(f"  Success rate: {success_rate:.1%}")

    @pytest.mark.asyncio
    async def test_historical_data_persistence(self, optimizer):
        """Test that historical patterns persist and are reloaded."""
        # Record some patterns
        await optimizer.record_feedback(
            model_id="gpt-4",
            use_case=UseCaseType.CONVERSATION,
            temperature=0.8,
            top_p=0.9,
            max_tokens=800,
            success_score=0.88
        )

        # Force save the patterns
        optimizer.learner._save_patterns()

        # Create a new optimizer instance (simulating restart)
        new_optimizer = ParameterOptimizer()

        # Check that patterns were loaded
        patterns = new_optimizer.learner.get_relevant_patterns(UseCaseType.CONVERSATION, "gpt-4")
        assert len(patterns) >= 1

        # Verify pattern data
        pattern = patterns[0]
        assert pattern.temperature == 0.8
        assert pattern.success_score == 0.88

    @pytest.mark.asyncio
    async def test_use_case_detection_integration(self, optimizer):
        """Test integration between use case detection and parameter optimization."""
        test_cases = [
            {
                'description': 'Write a creative poem about nature',
                'expected_use_case': UseCaseType.CREATIVE_WRITING,
                'expected_temp_range': (0.7, 1.2)
            },
            {
                'description': 'Generate JavaScript code for a web application',
                'expected_use_case': UseCaseType.CODE_GENERATION,
                'expected_temp_range': (0.1, 0.5)
            },
            {
                'description': 'Analyze sales data and identify trends',
                'expected_use_case': UseCaseType.ANALYSIS,
                'expected_temp_range': (0.1, 0.4)
            },
            {
                'description': 'Have a casual conversation about movies',
                'expected_use_case': UseCaseType.CONVERSATION,
                'expected_temp_range': (0.6, 0.9)
            }
        ]

        for case in test_cases:
            request = ParameterOptimizationRequest(
                model_id="gpt-4",
                user_description=case['description'],
                context=OptimizationContext(
                    model_id="gpt-4",
                    use_case=UseCaseType.OTHER,  # Let detection determine this
                    user_input_length=100,
                    conversation_history_length=0,
                    task_complexity_hint=None,
                    time_pressure=None
                )
            )

            response = await optimizer.optimize_parameters(request)

            # Check use case detection
            detected = response.use_case_detection.detected_use_case
            confidence = response.use_case_detection.confidence_score

            # Should detect the correct use case with reasonable confidence
            if detected == case['expected_use_case']:
                assert confidence >= 0.3, f"Low confidence {confidence} for {case['description']}"
            else:
                # If wrong, confidence should be lower
                assert confidence < 0.8, f"High confidence {confidence} for wrong detection: {detected} vs {case['expected_use_case']}"

            # Check parameter ranges
            temp = response.recommended_parameters.temperature
            min_temp, max_temp = case['expected_temp_range']
            assert min_temp <= temp <= max_temp, f"Temperature {temp} outside expected range [{min_temp}, {max_temp}] for {case['description']}"

    @pytest.mark.asyncio
    async def test_error_handling_and_fallbacks(self, optimizer):
        """Test error handling and fallback behavior."""
        # Test with invalid model ID (should still work with defaults)
        request = ParameterOptimizationRequest(
            model_id="",  # Invalid
            user_description="Do something",
            context=OptimizationContext(
                model_id="",
                use_case=UseCaseType.OTHER,
                user_input_length=0,
                conversation_history_length=0,
                task_complexity_hint=None,
                time_pressure=None
            )
        )

        response = await optimizer.optimize_parameters(request)

        # Should still return a valid response with fallback values
        assert isinstance(response, ParameterOptimizationResponse)
        assert response.recommended_parameters.temperature > 0
        assert response.optimization_confidence >= 0.0

        # Test smart defaults with no context
        defaults_request = SmartDefaultsRequest(
            model_id="unknown-model",
            user_context=None
        )

        defaults_response = await optimizer.get_smart_defaults(defaults_request)

        assert isinstance(defaults_response, SmartDefaultsResponse)
        assert defaults_response.default_parameters.temperature > 0
        assert defaults_response.confidence_score > 0


class TestGlobalIntegration:
    """Test integration with global functions."""

    @pytest.mark.asyncio
    async def test_global_functions_work(self):
        """Test that global convenience functions work correctly."""
        # Test optimize_parameters global function
        request = ParameterOptimizationRequest(
            model_id="gpt-4",
            user_description="Debug this error in my JavaScript application",
            context=OptimizationContext(
                model_id="gpt-4",
                use_case=UseCaseType.DEBUGGING,
                user_input_length=300,
                conversation_history_length=1,
                task_complexity_hint=None,
                time_pressure=None
            )
        )

        response = await optimize_parameters(request)

        assert isinstance(response, ParameterOptimizationResponse)
        assert response.use_case_detection.detected_use_case == UseCaseType.DEBUGGING

        # Test get_smart_defaults global function
        defaults_request = SmartDefaultsRequest(
            model_id="claude",
            user_context="I analyze documents"
        )

        defaults_response = await get_smart_defaults(defaults_request)

        assert isinstance(defaults_response, SmartDefaultsResponse)
        assert defaults_response.default_parameters.temperature < 0.5  # Analysis should be low temp


class TestPerformanceBenchmarks:
    """Performance benchmark tests to ensure requirements are met."""

    @pytest.mark.asyncio
    async def test_response_time_under_2_seconds(self):
        """Benchmark test ensuring <2 second response times."""
        optimizer = ParameterOptimizer()

        # Warm up the cache
        warmup_request = ParameterOptimizationRequest(
            model_id="gpt-4",
            user_description="warmup",
            context=OptimizationContext(
                model_id="gpt-4",
                use_case=UseCaseType.OTHER,
                user_input_length=10,
                conversation_history_length=0,
                task_complexity_hint=None,
                time_pressure=None
            )
        )
        await optimizer.optimize_parameters(warmup_request)

        # Benchmark actual requests
        benchmark_times = []

        for i in range(100):  # Test 100 requests
            request = ParameterOptimizationRequest(
                model_id="gpt-4",
                user_description=f"Benchmark request {i}",
                context=OptimizationContext(
                    model_id="gpt-4",
                    use_case=UseCaseType.ANALYSIS,
                    user_input_length=100 + (i % 50),  # Vary input length
                    conversation_history_length=i % 10,  # Vary history
                    task_complexity_hint=None,
                    time_pressure=None
                )
            )

            start_time = time.time()
            response = await optimizer.optimize_parameters(request)
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000
            benchmark_times.append(response_time_ms)

            # Each individual request must be under 2 seconds
            assert response_time_ms < 2000, f"Request {i} took {response_time_ms:.1f}ms (>2s limit)"

        # Analyze benchmark results
        avg_time = sum(benchmark_times) / len(benchmark_times)
        p95_time = sorted(benchmark_times)[int(len(benchmark_times) * 0.95)]
        max_time = max(benchmark_times)

        print(f"Performance benchmark results (100 requests):")
        print(f"  Average: {avg_time:.1f}ms")
        print(f"  95th percentile: {p95_time:.1f}ms")
        print(f"  Maximum: {max_time:.1f}ms")

        # Requirements check
        assert avg_time < 2000, f"Average response time {avg_time:.1f}ms exceeds 2s requirement"
        assert p95_time < 2000, f"95th percentile {p95_time:.1f}ms exceeds 2s requirement"

        # Most requests should be fast (cached)
        fast_requests = sum(1 for t in benchmark_times if t < 100)
        assert fast_requests > len(benchmark_times) * 0.8, f"Only {fast_requests}/{len(benchmark_times)} requests were fast (<100ms)"