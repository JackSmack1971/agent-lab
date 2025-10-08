#!/usr/bin/env python3
"""Performance benchmark script for parameter optimizer."""

import asyncio
import json
import statistics
import time
from pathlib import Path

from src.services.parameter_optimizer import ParameterOptimizer
from src.models.parameter_optimization import (
    UseCaseType,
    ParameterOptimizationRequest,
    OptimizationContext,
    SmartDefaultsRequest,
)


async def benchmark_parameter_optimization():
    """Benchmark parameter optimization performance."""
    print("🚀 Starting Parameter Optimizer Performance Benchmark")
    print("=" * 60)

    optimizer = ParameterOptimizer()

    # Test configurations
    test_configs = [
        {
            'name': 'Creative Writing',
            'use_case': UseCaseType.CREATIVE_WRITING,
            'description': 'Write a creative short story about artificial intelligence'
        },
        {
            'name': 'Code Generation',
            'use_case': UseCaseType.CODE_GENERATION,
            'description': 'Generate Python code for a machine learning algorithm'
        },
        {
            'name': 'Analysis',
            'use_case': UseCaseType.ANALYSIS,
            'description': 'Analyze this dataset and identify key patterns'
        },
        {
            'name': 'Summarization',
            'use_case': UseCaseType.SUMMARIZATION,
            'description': 'Summarize this long research paper'
        },
        {
            'name': 'Conversation',
            'use_case': UseCaseType.CONVERSATION,
            'description': 'Have a friendly chat about current technology trends'
        }
    ]

    models = ['gpt-4', 'claude-3', 'gemini-pro']

    # Individual request benchmark
    print("\n📊 Individual Request Performance")
    print("-" * 40)

    individual_times = []

    for config in test_configs:
        for model in models:
            request = ParameterOptimizationRequest(
                model_id=model,
                user_description=config['description'],
                context=OptimizationContext(
                    model_id=model,
                    use_case=config['use_case'],
                    user_input_length=150,
                    conversation_history_length=5,
                    task_complexity_hint=None,
                    time_pressure=None
                )
            )

            # Warm up
            await optimizer.optimize_parameters(request)

            # Benchmark
            start_time = time.time()
            response = await optimizer.optimize_parameters(request)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            individual_times.append(response_time)

            status = "✅" if response_time < 2000 else "❌"
            print(f"{status} {config['name'][:15]:<15} {model:<12} {response_time:>8.1f}ms")

    # Individual stats
    avg_individual = statistics.mean(individual_times)
    p95_individual = statistics.quantiles(individual_times, n=20)[18]  # 95th percentile
    max_individual = max(individual_times)

    print(f"\n📈 Individual Request Statistics:")
    print(f"   Average: {avg_individual:.1f}ms")
    print(f"   95th percentile: {p95_individual:.1f}ms")
    print(f"   Maximum: {max_individual:.1f}ms")
    print(f"   All < 2s: {'✅' if max_individual < 2000 else '❌'}")

    # Concurrent load test
    print("\n🔄 Concurrent Load Test (100 simultaneous requests)")
    print("-" * 50)

    async def concurrent_worker(worker_id):
        config = test_configs[worker_id % len(test_configs)]
        model = models[worker_id % len(models)]

        request = ParameterOptimizationRequest(
            model_id=model,
            user_description=f"{config['description']} - Request {worker_id}",
            context=OptimizationContext(
                model_id=model,
                use_case=config['use_case'],
                user_input_length=100 + (worker_id % 100),
                conversation_history_length=worker_id % 10,
                task_complexity_hint=None,
                time_pressure=None
            )
        )

        start_time = time.time()
        response = await optimizer.optimize_parameters(request)
        end_time = time.time()

        response_time = (end_time - start_time) * 1000

        return {
            'worker_id': worker_id,
            'response_time': response_time,
            'success': response_time < 2000,
            'use_case': config['name'],
            'model': model
        }

    # Run concurrent test
    concurrent_start = time.time()
    tasks = [concurrent_worker(i) for i in range(100)]
    concurrent_results = await asyncio.gather(*tasks)
    concurrent_end = time.time()

    concurrent_times = [r['response_time'] for r in concurrent_results]
    concurrent_successes = sum(1 for r in concurrent_results if r['success'])

    avg_concurrent = statistics.mean(concurrent_times)
    p95_concurrent = statistics.quantiles(concurrent_times, n=20)[18]
    max_concurrent = max(concurrent_times)
    total_concurrent_time = (concurrent_end - concurrent_start) * 1000

    print(f"   Total time: {total_concurrent_time:.1f}ms")
    print(f"   Average per request: {avg_concurrent:.1f}ms")
    print(f"   95th percentile: {p95_concurrent:.1f}ms")
    print(f"   Maximum: {max_concurrent:.1f}ms")
    print(f"   Success rate: {concurrent_successes}/100 ({concurrent_successes}%)")

    # Cache effectiveness test
    print("\n💾 Cache Effectiveness Test")
    print("-" * 30)

    cache_request = ParameterOptimizationRequest(
        model_id="gpt-4",
        user_description="Cached request for creative writing",
        context=OptimizationContext(
            model_id="gpt-4",
            use_case=UseCaseType.CREATIVE_WRITING,
            user_input_length=100,
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure=None
        )
    )

    # Clear cache and measure first request
    optimizer._optimization_cache.clear()
    start_time = time.time()
    response1 = await optimizer.optimize_parameters(cache_request)
    first_time = (time.time() - start_time) * 1000

    # Measure cached request
    start_time = time.time()
    response2 = await optimizer.optimize_parameters(cache_request)
    cached_time = (time.time() - start_time) * 1000

    cache_speedup = first_time / cached_time if cached_time > 0 else float('inf')

    print(f"   First request: {first_time:.1f}ms")
    print(f"   Cached request: {cached_time:.1f}ms")
    print(f"   Speedup: {cache_speedup:.1f}x faster")

    # Smart defaults performance
    print("\n🎯 Smart Defaults Performance")
    print("-" * 32)

    defaults_times = []
    for i in range(50):
        request = SmartDefaultsRequest(
            model_id="gpt-4",
            user_context=f"Context {i}: I write code and analyze data"
        )

        start_time = time.time()
        response = await optimizer.get_smart_defaults(request)
        end_time = time.time()

        response_time = (end_time - start_time) * 1000
        defaults_times.append(response_time)

    avg_defaults = statistics.mean(defaults_times)
    max_defaults = max(defaults_times)

    print(f"   Average: {avg_defaults:.1f}ms")
    print(f"   Maximum: {max_defaults:.1f}ms")
    print(f"   All < 2s: {'✅' if max_defaults < 2000 else '❌'}")

    # Use case detection accuracy
    print("\n🎯 Use Case Detection Accuracy")
    print("-" * 33)

    accuracy_tests = [
        ("Write a creative story about time travel", UseCaseType.CREATIVE_WRITING),
        ("Generate Python code for data processing", UseCaseType.CODE_GENERATION),
        ("Analyze sales data trends", UseCaseType.ANALYSIS),
        ("Summarize this research paper", UseCaseType.SUMMARIZATION),
        ("Let's chat about movies", UseCaseType.CONVERSATION),
        ("Debug this JavaScript error", UseCaseType.DEBUGGING),
        ("Translate English to Spanish", UseCaseType.TRANSLATION),
        ("Solve this math problem step by step", UseCaseType.REASONING),
    ]

    correct_detections = 0
    total_tests = len(accuracy_tests)

    for text, expected in accuracy_tests:
        result = optimizer.detector.detect_use_case(text)
        if result.detected_use_case == expected and result.confidence_score > 0.6:
            correct_detections += 1
            status = "✅"
        else:
            status = "❌"

        print(f"{status} {text[:30]:<30} → {result.detected_use_case.value.replace('_', ' '):<15} ({result.confidence_score:.2f})")

    accuracy = correct_detections / total_tests * 100
    print(f"\n   Accuracy: {accuracy:.1f}% ({correct_detections}/{total_tests})")
    print(f"   >80% requirement: {'✅' if accuracy > 80 else '❌'}")

    # Overall assessment
    print("\n🏆 Overall Assessment")
    print("=" * 20)

    requirements_met = 0
    total_requirements = 0

    # Performance requirements
    total_requirements += 1
    if avg_individual < 2000:
        requirements_met += 1
        print("✅ Average response time < 2s")
    else:
        print("❌ Average response time >= 2s")

    total_requirements += 1
    if max_individual < 2000:
        requirements_met += 1
        print("✅ All individual requests < 2s")
    else:
        print("❌ Some individual requests >= 2s")

    total_requirements += 1
    if concurrent_successes == 100:
        requirements_met += 1
        print("✅ Handles 100+ concurrent requests")
    else:
        print("❌ Failed concurrent load test")

    # Accuracy requirements
    total_requirements += 1
    if accuracy > 80:
        requirements_met += 1
        print("✅ Use case detection accuracy > 80%")
    else:
        print("❌ Use case detection accuracy <= 80%")

    # Cache effectiveness
    total_requirements += 1
    if cache_speedup > 10:
        requirements_met += 1
        print("✅ Effective caching (>10x speedup)")
    else:
        print("❌ Poor cache effectiveness")

    print(f"\n📊 Requirements Met: {requirements_met}/{total_requirements} ({requirements_met/total_requirements*100:.1f}%)")

    if requirements_met == total_requirements:
        print("🎉 ALL REQUIREMENTS MET! Parameter optimizer is production-ready.")
        return True
    else:
        print("⚠️  Some requirements not met. Review and optimize.")
        return False


async def main():
    """Main benchmark function."""
    try:
        success = await benchmark_parameter_optimization()

        # Save benchmark results
        results_file = Path("benchmark_results.json")
        benchmark_data = {
            "timestamp": time.time(),
            "requirements_met": success,
            "version": "1.0.0"
        }

        with open(results_file, 'w') as f:
            json.dump(benchmark_data, f, indent=2)

        print(f"\n💾 Results saved to {results_file}")

        return 0 if success else 1

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())