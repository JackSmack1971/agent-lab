"""Cost calculation utilities for AI model API calls."""

from typing import Union


# Cost per 1K tokens (approximate rates as of 2024)
MODEL_COSTS = {
    "gpt-4": {
        "input_per_1k": 0.03,
        "output_per_1k": 0.06,
    },
    "gpt-3.5-turbo": {
        "input_per_1k": 0.0015,
        "output_per_1k": 0.002,
    },
    "claude-3-opus": {
        "input_per_1k": 0.015,
        "output_per_1k": 0.075,
    },
    "claude-3-sonnet": {
        "input_per_1k": 0.003,
        "output_per_1k": 0.015,
    },
    "claude-3-haiku": {
        "input_per_1k": 0.00025,
        "output_per_1k": 0.00125,
    },
    "meta-llama/llama-3-70b": {
        "input_per_1k": 0.001,
        "output_per_1k": 0.002,
    },
    "openai/gpt-4o-mini": {
        "input_per_1k": 0.00015,
        "output_per_1k": 0.0006,
    },
}


def calculate_cost(
    input_tokens: Union[int, float],
    output_tokens: Union[int, float],
    model: str
) -> float:
    """
    Calculate the cost of an API call based on token usage and model.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        model: Model identifier (e.g., "gpt-4", "claude-3-opus")

    Returns:
        Cost in USD (float)

    Raises:
        ValueError: If model is not supported or token values are invalid
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("Token counts cannot be negative")

    if not isinstance(input_tokens, (int, float)) or not isinstance(output_tokens, (int, float)):
        raise ValueError("Token counts must be numeric")

    # Normalize model name (remove provider prefix if present)
    normalized_model = model.split("/")[-1] if "/" in model else model

    if normalized_model not in MODEL_COSTS:
        # Default to GPT-3.5-turbo pricing for unknown models
        normalized_model = "gpt-3.5-turbo"

    costs = MODEL_COSTS[normalized_model]

    # Calculate cost per 1K tokens, then convert to actual token count
    input_cost = (input_tokens / 1000) * costs["input_per_1k"]
    output_cost = (output_tokens / 1000) * costs["output_per_1k"]

    total_cost = input_cost + output_cost

    return round(total_cost, 6)  # Round to microcents precision


def get_supported_models() -> list[str]:
    """Get list of supported models for cost calculation."""
    return list(MODEL_COSTS.keys())


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text string.

    This is a rough approximation: ~4 characters per token for English text.

    Args:
        text: Input text string

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Rough approximation: 1 token per 4 characters
    return max(1, len(text) // 4)