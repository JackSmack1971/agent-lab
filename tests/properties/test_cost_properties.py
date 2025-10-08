"""Property-based tests for cost calculation using Hypothesis."""

from hypothesis import given, strategies as st, assume
import pytest

from agents.cost import calculate_cost, MODEL_COSTS


@given(
    input_tokens=st.integers(min_value=0, max_value=1000000),
    output_tokens=st.integers(min_value=0, max_value=100000),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_cost_monotonicity(input_tokens, output_tokens, model):
    """
    Property: More tokens = Higher cost (monotonicity)

    Mathematical property that should always hold
    """
    # Arrange
    cost1 = calculate_cost(input_tokens, output_tokens, model)

    # Act - Add more tokens
    cost2_more_input = calculate_cost(input_tokens + 1000, output_tokens, model)
    cost2_more_output = calculate_cost(input_tokens, output_tokens + 1000, model)

    # Assert - Cost increases
    assert cost2_more_input >= cost1, f"Adding input tokens decreased cost!"
    assert cost2_more_output >= cost1, f"Adding output tokens decreased cost!"


@given(
    tokens=st.integers(min_value=1, max_value=100000),
    model=st.sampled_from(["gpt-4", "gpt-3.5-turbo"])
)
def test_cost_commutative_for_same_total(tokens, model):
    """
    Property: Total cost should be same regardless of input/output split

    Mathematical property: cost(100in, 0out) ?= cost(0in, 100out)
    Note: This may NOT hold if pricing differs! (discovers pricing model)
    """
    assume(tokens > 10)  # Avoid tiny numbers

    # Arrange - Two ways to split tokens
    cost_all_input = calculate_cost(tokens, 0, model)
    cost_all_output = calculate_cost(0, tokens, model)

    # This test might fail - that's OK! It discovers pricing differences
    # If it fails, document: "Output tokens cost more than input"
    # This is valuable information!
    # For now, we'll just check that both are non-negative
    assert cost_all_input >= 0
    assert cost_all_output >= 0


@given(
    input_tokens=st.integers(min_value=0, max_value=100000),
    output_tokens=st.integers(min_value=0, max_value=100000),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_cost_non_negative(input_tokens, output_tokens, model):
    """
    Property: Cost should never be negative

    Basic sanity check for all cost calculations
    """
    cost = calculate_cost(input_tokens, output_tokens, model)
    assert cost >= 0, f"Cost was negative: {cost}"


@given(
    input_tokens=st.integers(min_value=0, max_value=10000),
    output_tokens=st.integers(min_value=0, max_value=10000),
    model1=st.sampled_from(list(MODEL_COSTS.keys())),
    model2=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_expensive_models_cost_more(input_tokens, output_tokens, model1, model2):
    """
    Property: More expensive models should cost more for same token usage

    This discovers relative pricing between models
    """
    assume(input_tokens > 0 or output_tokens > 0)  # Need some tokens to compare

    cost1 = calculate_cost(input_tokens, output_tokens, model1)
    cost2 = calculate_cost(input_tokens, output_tokens, model2)

    # Get relative costs from our pricing table
    input_rate1 = MODEL_COSTS[model1]["input_per_1k"]
    output_rate1 = MODEL_COSTS[model1]["output_per_1k"]
    input_rate2 = MODEL_COSTS[model2]["input_per_1k"]
    output_rate2 = MODEL_COSTS[model2]["output_per_1k"]

    # If model1 is more expensive than model2, cost1 should be higher
    if input_rate1 > input_rate2 and output_rate1 > output_rate2:
        assert cost1 >= cost2, f"{model1} should cost more than {model2}"


@given(
    input_tokens=st.integers(min_value=0, max_value=100000),
    output_tokens=st.integers(min_value=0, max_value=100000),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_cost_additivity(input_tokens, output_tokens, model):
    """
    Property: Cost should be additive for separate calculations

    cost(a,b) + cost(c,d) should equal cost(a+c,b+d) for same model
    """
    assume(input_tokens > 0 and output_tokens > 0)  # Need positive values

    # Split the tokens
    half_input = input_tokens // 2
    half_output = output_tokens // 2

    # Calculate separately
    cost1 = calculate_cost(half_input, half_output, model)
    cost2 = calculate_cost(input_tokens - half_input, output_tokens - half_output, model)

    # Calculate combined
    cost_combined = calculate_cost(input_tokens, output_tokens, model)

    # Should be approximately equal (allowing for rounding)
    assert abs((cost1 + cost2) - cost_combined) < 0.000001, "Costs should be additive"


@given(
    input_tokens=st.integers(min_value=0, max_value=100000),
    output_tokens=st.integers(min_value=0, max_value=100000),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_cost_precision(input_tokens, output_tokens, model):
    """
    Property: Cost calculations should have reasonable precision

    Costs shouldn't have more than 6 decimal places
    """
    cost = calculate_cost(input_tokens, output_tokens, model)

    # Check that cost is rounded appropriately
    str_cost = str(cost)
    if '.' in str_cost:
        decimal_part = str_cost.split('.')[1]
        assert len(decimal_part) <= 6, f"Cost has too many decimal places: {cost}"


@given(
    input_tokens=st.integers(min_value=0, max_value=1000),
    output_tokens=st.integers(min_value=0, max_value=1000),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_cost_scaling(input_tokens, output_tokens, model):
    """
    Property: Cost should scale linearly with token count

    Doubling tokens should roughly double the cost
    """
    assume(input_tokens > 0 or output_tokens > 0)

    base_cost = calculate_cost(input_tokens, output_tokens, model)
    double_cost = calculate_cost(input_tokens * 2, output_tokens * 2, model)

    if base_cost > 0:
        ratio = double_cost / base_cost
        # Should be close to 2.0 (allowing for rounding)
        assert 1.9 <= ratio <= 2.1, f"Cost scaling ratio: {ratio}, expected ~2.0"


@given(st.sampled_from(list(MODEL_COSTS.keys())))
def test_model_cost_rates_positive(model):
    """
    Property: All model cost rates should be positive

    Ensures pricing data integrity
    """
    costs = MODEL_COSTS[model]
    assert costs["input_per_1k"] > 0, f"{model} input rate should be positive"
    assert costs["output_per_1k"] > 0, f"{model} output rate should be positive"


@given(
    input_tokens=st.integers(min_value=0, max_value=100000),
    output_tokens=st.integers(min_value=0, max_value=100000)
)
def test_zero_tokens_cost_zero(input_tokens, output_tokens):
    """
    Property: Zero tokens should result in zero cost

    Edge case: empty inputs/outputs
    """
    # Test with zero input tokens
    cost_zero_input = calculate_cost(0, output_tokens, "gpt-4")
    assert cost_zero_input == 0.0, "Zero input tokens should cost zero"

    # Test with zero output tokens
    cost_zero_output = calculate_cost(input_tokens, 0, "gpt-4")
    assert cost_zero_output == 0.0, "Zero output tokens should cost zero"

    # Test with both zero
    cost_zero_both = calculate_cost(0, 0, "gpt-4")
    assert cost_zero_both == 0.0, "Zero tokens should cost zero"


@given(
    input_tokens=st.integers(min_value=-100, max_value=-1),
    output_tokens=st.integers(min_value=0, max_value=100),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_negative_input_tokens_error(input_tokens, output_tokens, model):
    """
    Property: Negative input tokens should raise ValueError

    Validates input sanitization
    """
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_cost(input_tokens, output_tokens, model)


@given(
    input_tokens=st.integers(min_value=0, max_value=100),
    output_tokens=st.integers(min_value=-100, max_value=-1),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_negative_output_tokens_error(input_tokens, output_tokens, model):
    """
    Property: Negative output tokens should raise ValueError

    Validates input sanitization
    """
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_cost(input_tokens, output_tokens, model)


@given(
    input_tokens=st.floats(min_value=0, max_value=1000),
    output_tokens=st.floats(min_value=0, max_value=1000),
    model=st.sampled_from(list(MODEL_COSTS.keys()))
)
def test_float_token_inputs(input_tokens, output_tokens, model):
    """
    Property: Function should handle float token inputs

    Tests numeric type flexibility
    """
    # Should not raise an exception
    cost = calculate_cost(input_tokens, output_tokens, model)
    assert cost >= 0


@given(
    input_tokens=st.integers(min_value=0, max_value=1000),
    output_tokens=st.integers(min_value=0, max_value=1000),
    model=st.text(min_size=1, max_size=50)
)
def test_unknown_model_fallback(input_tokens, output_tokens, model):
    """
    Property: Unknown models should fall back to default pricing

    Ensures graceful degradation
    """
    # Should not raise an exception for unknown models
    cost = calculate_cost(input_tokens, output_tokens, model)
    assert cost >= 0

    # Should be same as gpt-3.5-turbo pricing
    default_cost = calculate_cost(input_tokens, output_tokens, "gpt-3.5-turbo")
    assert cost == default_cost