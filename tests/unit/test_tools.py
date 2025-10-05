"""Unit tests for tools module."""

from unittest.mock import Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic_ai import RunContext

from agents.tools import AddInput, NowInput, add_numbers, utc_now


class TestTools:
    """Test suite for tools functionality."""

    @pytest.mark.asyncio
    async def test_add_numbers_returns_correct_sum(self) -> None:
        """Test that add_numbers returns the correct sum of two numbers."""
        ctx = Mock(spec=RunContext)
        input_data = AddInput(a=5.5, b=3.2)
        result = await add_numbers(ctx, input_data)
        assert result == 8.7

    @pytest.mark.asyncio
    async def test_add_numbers_handles_negative_numbers(self) -> None:
        """Test that add_numbers handles negative numbers correctly."""
        ctx = Mock(spec=RunContext)
        input_data = AddInput(a=-2.0, b=4.0)
        result = await add_numbers(ctx, input_data)
        assert result == 2.0

    @pytest.mark.asyncio
    async def test_add_numbers_returns_float_type(self) -> None:
        """Test that add_numbers returns a float type."""
        ctx = Mock(spec=RunContext)
        input_data = AddInput(a=1, b=2)
        result = await add_numbers(ctx, input_data)
        assert isinstance(result, float)
        assert result == 3.0

    @pytest.mark.asyncio
    async def test_utc_now_includes_utc_suffix(self) -> None:
        """Test that utc_now includes UTC suffix in default format."""
        ctx = Mock(spec=RunContext)
        input_data = NowInput()
        result = await utc_now(ctx, input_data)
        assert "UTC" in result

    @pytest.mark.asyncio
    async def test_utc_now_respects_custom_format(self) -> None:
        """Test that utc_now respects custom format strings."""
        ctx = Mock(spec=RunContext)
        custom_fmt = "%Y/%m/%d %H:%M:%S"
        input_data = NowInput(fmt=custom_fmt)
        result = await utc_now(ctx, input_data)
        # Should not contain default UTC suffix when using custom format
        assert "UTC" not in result

    @pytest.mark.asyncio
    async def test_utc_now_returns_current_time(self) -> None:
        """Test that utc_now returns current time within 1 second tolerance."""
        import time
        from datetime import datetime, timezone

        ctx = Mock(spec=RunContext)
        input_data = NowInput()
        start_time = time.time()
        result = await utc_now(ctx, input_data)
        end_time = time.time()

        # Parse the result using the default format
        parsed = datetime.strptime(result, "%Y-%m-%d %H:%M:%S UTC")
        # Make it timezone aware
        parsed = parsed.replace(tzinfo=timezone.utc)
        result_timestamp = parsed.timestamp()

        # Check that result is within 1 second of current time
        assert abs(result_timestamp - start_time) <= 1
        assert abs(result_timestamp - end_time) <= 1

    @given(
        a=st.floats(allow_nan=False, allow_infinity=False),
        b=st.floats(allow_nan=False, allow_infinity=False),
    )
    @pytest.mark.asyncio
    async def test_add_numbers_commutative(self, a: float, b: float) -> None:
        """Property test: addition is commutative (a + b = b + a)."""
        ctx = Mock(spec=RunContext)
        result_ab = await add_numbers(ctx, AddInput(a=a, b=b))
        result_ba = await add_numbers(ctx, AddInput(a=b, b=a))
        assert result_ab == result_ba

    @given(
        a=st.floats(
            min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
        ),
        b=st.floats(
            min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
        ),
    )
    @pytest.mark.asyncio
    async def test_add_numbers_correctness(self, a: float, b: float) -> None:
        """Property test: add_numbers returns the correct sum a + b."""
        ctx = Mock(spec=RunContext)
        result = await add_numbers(ctx, AddInput(a=a, b=b))
        assert result == a + b

    @given(a=st.floats(allow_nan=False, allow_infinity=False))
    @pytest.mark.asyncio
    async def test_add_numbers_identity(self, a: float) -> None:
        """Property test: zero is the identity element (a + 0 = a)."""
        ctx = Mock(spec=RunContext)
        result = await add_numbers(ctx, AddInput(a=a, b=0.0))
        assert result == a
