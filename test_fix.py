#!/usr/bin/env python3
"""Test the fix for debug detection."""

from src.services.parameter_optimizer import UseCaseDetector
from src.models.parameter_optimization import UseCaseType

def test_debug_detection():
    detector = UseCaseDetector()

    text = "Debug this error in my JavaScript application"
    result = detector.detect_use_case(text)

    print(f"Text: {text}")
    print(f"Detected: {result.detected_use_case}")
    print(f"Expected: {UseCaseType.DEBUGGING}")
    print(f"Confidence: {result.confidence_score}")
    print(f"Keywords: {result.keywords_matched}")

    if result.detected_use_case == UseCaseType.DEBUGGING:
        print("✓ FIXED: Correctly detected as DEBUGGING")
        return True
    else:
        print("✗ STILL BROKEN: Still detecting as", result.detected_use_case)
        return False

if __name__ == "__main__":
    test_debug_detection()