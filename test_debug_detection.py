#!/usr/bin/env python3
"""Quick test script to verify use case detection fix."""

from src.services.parameter_optimizer import UseCaseDetector
from src.models.parameter_optimization import UseCaseType

def test_accuracy():
    detector = UseCaseDetector()

    # Test cases with expected results
    test_cases = [
        ("I want to write a creative story about AI taking over the world", UseCaseType.CREATIVE_WRITING),
        ("Generate Python code for a neural network", UseCaseType.CODE_GENERATION),
        ("Analyze this dataset and find patterns in customer behavior", UseCaseType.ANALYSIS),
        ("Summarize this long article about climate change", UseCaseType.SUMMARIZATION),
        ("Let's chat about your favorite movies", UseCaseType.CONVERSATION),
        ("Debug this JavaScript error in my web application", UseCaseType.DEBUGGING),
        ("Translate this English text to French", UseCaseType.TRANSLATION),
        ("Solve this complex mathematical problem step by step", UseCaseType.REASONING),
    ]

    correct_detections = 0
    total_cases = len(test_cases)

    print("Testing use case detection accuracy:")
    print("=" * 50)

    for text, expected_use_case in test_cases:
        result = detector.detect_use_case(text)
        is_correct = result.detected_use_case == expected_use_case and result.confidence_score > 0.3

        status = "✓" if is_correct else "✗"
        print(f"{status} {text[:50]}...")
        print(f"   Expected: {expected_use_case.value}, Got: {result.detected_use_case.value}, Confidence: {result.confidence_score:.2f}")
        print(f"   Keywords: {result.keywords_matched}")

        if is_correct:
            correct_detections += 1
        print()

    accuracy = correct_detections / total_cases
    print(f"Accuracy: {correct_detections}/{total_cases} = {accuracy:.1%}")

    if accuracy > 0.8:
        print("✓ PASSED: Accuracy above 80%")
        return True
    else:
        print("✗ FAILED: Accuracy below 80%")
        return False

if __name__ == "__main__":
    test_accuracy()