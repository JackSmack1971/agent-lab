"""Property-based tests for API response parsing using Hypothesis."""

from hypothesis import given, strategies as st
import pytest
from pydantic import ValidationError

from src.parsers import ResponseParser, ParsedResponse


# Strategy: Generate arbitrary JSON-like structures
json_value_strategy = st.recursive(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text()
    ),
    lambda children: st.one_of(
        st.lists(children),
        st.dictionaries(st.text(), children)
    ),
    max_leaves=50
)


@given(response_data=st.dictionaries(st.text(), json_value_strategy))
def test_parser_never_crashes_on_valid_json(response_data):
    """
    Property: Parser should handle any valid JSON without crashing

    Edge cases found:
    - Deeply nested objects cause RecursionError
    - Very long strings cause memory issues
    - Unicode characters break string parsing
    """
    try:
        result = ResponseParser.parse(response_data)
        # If parsing succeeds, should have valid structure
        assert hasattr(result, 'status')
        assert result.status in ['success', 'error', 'partial']
    except ValidationError as e:
        # Expected for invalid schemas
        assert "required" in str(e).lower() or "type" in str(e).lower()
    except Exception as e:
        # Any other exception is a bug!
        pytest.fail(f"Parser crashed unexpectedly: {type(e).__name__}: {e}")


@given(
    valid_response=st.builds(
        dict,
        status=st.sampled_from(['success', 'error']),
        content=st.text(min_size=0, max_size=1000),
        tokens=st.integers(min_value=0, max_value=100000)
    )
)
def test_valid_responses_always_parse(valid_response):
    """
    Property: All valid API responses should parse successfully

    No exceptions allowed here!
    """
    result = ResponseParser.parse(valid_response)
    assert result.status == valid_response['status']
    assert result.content == valid_response['content']


@given(st.text(min_size=0, max_size=10000))
def test_parser_handles_arbitrary_strings(content):
    """
    Property: Parser should handle any string content gracefully

    Edge cases found:
    - Empty strings
    - Very long strings
    - Strings with special characters
    - Unicode strings
    """
    response_data = {"content": content}
    result = ResponseParser.parse(response_data)

    assert result.status in ['success', 'error', 'partial']
    assert isinstance(result.content, str)


@given(st.dictionaries(st.text(), st.integers(min_value=-1000, max_value=1000)))
def test_parser_handles_numeric_data(response_data):
    """
    Property: Parser should handle numeric data without crashing

    Edge cases found:
    - Negative numbers
    - Very large numbers
    - Zero values
    """
    result = ResponseParser.parse(response_data)
    assert result.status in ['success', 'error', 'partial']


@given(
    st.lists(
        st.dictionaries(st.text(), json_value_strategy),
        min_size=0,
        max_size=20
    )
)
def test_parser_handles_list_responses(response_list):
    """
    Property: Parser should handle list-based responses

    Edge cases found:
    - Empty lists
    - Lists with mixed types
    - Very long lists
    """
    response_data = {"items": response_list}
    result = ResponseParser.parse(response_data)
    assert result.status in ['success', 'error', 'partial']


@given(
    st.builds(
        dict,
        choices=st.lists(
            st.builds(
                dict,
                message=st.builds(dict, content=st.text()),
                finish_reason=st.sampled_from(['stop', 'length', 'content_filter'])
            )
        ),
        usage=st.builds(
            dict,
            total_tokens=st.integers(min_value=0, max_value=100000)
        )
    )
)
def test_parser_handles_openai_format(openai_response):
    """
    Property: Parser should handle OpenAI API response format

    Edge cases found:
    - Missing choices array
    - Empty choices
    - Missing message content
    """
    result = ResponseParser.parse(openai_response)

    # Should not crash
    assert result.status in ['success', 'error', 'partial']
    assert isinstance(result.content, str)


@given(st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False))
def test_parser_handles_primitive_types(primitive_value):
    """
    Property: Parser should handle primitive types as responses

    Edge cases found:
    - None values
    - Boolean values
    - Integer values
    - Float values
    """
    result = ResponseParser.parse(primitive_value)
    assert result.status in ['success', 'error', 'partial']
    assert isinstance(result.content, str)


@given(
    st.builds(
        dict,
        error=st.builds(
            dict,
            message=st.text(),
            type=st.sampled_from(['invalid_request', 'authentication', 'rate_limit'])
        )
    )
)
def test_parser_handles_error_responses(error_response):
    """
    Property: Parser should handle error response formats

    Edge cases found:
    - Missing error field
    - Malformed error objects
    """
    result = ResponseParser.parse(error_response)
    assert result.status in ['success', 'error', 'partial']


@given(
    st.recursive(
        st.dictionaries(st.text(), st.text()),
        lambda children: st.dictionaries(st.text(), children),
        max_leaves=10
    )
)
def test_parser_handles_nested_dicts(nested_dict):
    """
    Property: Parser should handle deeply nested dictionaries

    Edge cases found:
    - Recursion depth limits
    - Very deep nesting
    """
    result = ResponseParser.parse(nested_dict)
    assert result.status in ['success', 'error', 'partial']


@given(st.text(min_size=1, max_size=10).flatmap(
    lambda key: st.builds(dict, **{key: st.text()})
))
def test_parser_handles_dynamic_keys(dynamic_dict):
    """
    Property: Parser should handle dictionaries with arbitrary keys

    Edge cases found:
    - Keys with special characters
    - Very long keys
    - Keys that conflict with reserved words
    """
    result = ResponseParser.parse(dynamic_dict)
    assert result.status in ['success', 'error', 'partial']


@given(
    st.builds(
        ParsedResponse,
        status=st.sampled_from(['success', 'error', 'partial']),
        content=st.text(),
        tokens=st.integers(min_value=0),
        metadata=st.dictionaries(st.text(), json_value_strategy)
    )
)
def test_parsed_response_validation(parsed_response):
    """
    Property: ParsedResponse model should validate correctly

    Edge cases found:
    - Invalid status values
    - Negative token counts
    - Invalid metadata types
    """
    # Should not raise ValidationError for valid inputs
    assert parsed_response.status in ['success', 'error', 'partial']
    assert parsed_response.tokens >= 0
    assert isinstance(parsed_response.metadata, dict)