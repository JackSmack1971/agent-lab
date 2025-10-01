"""Unit tests for tools module."""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from hypothesis import given, strategies as st

from agents.tools import add_numbers, utc_now, AddInput, NowInput
from pydantic_ai import RunContext


class TestTools:
    """Test suite for tools functionality."""

    @pytest.mark.asyncio
    async def test_add_numbers_basic(self) -> None:
        """Test basic addition of two positive numbers."""
        ctx = Mock(spec=RunContext)
        input_data = AddInput(a=5.5, b=3.2)
        result = await add_numbers(ctx, input_data)
        assert result == 8.7

    @pytest.mark.asyncio
    async def test_add_numbers_negative(self) -> None:
        """Test addition with negative numbers."""
        ctx = Mock(spec=RunContext)
        input_data = AddInput(a=-2.0, b=4.0)
        result = await add_numbers(ctx, input_data)
        assert result == 2.0

    @pytest.mark.asyncio
    async def test_add_numbers_zero(self) -> None:
        """Test addition with zero."""
        ctx = Mock(spec=RunContext)
        input_data = AddInput(a=0.0, b=5.0)
        result = await add_numbers(ctx, input_data)
        assert result == 5.0

    @pytest.mark.asyncio
    async def test_utc_now_default_format(self) -> None:
        """Test utc_now returns current UTC time in ISO format."""
        ctx = Mock(spec=RunContext)
        input_data = NowInput()
        result = await utc_now(ctx, input_data)
        # Should be ISO format string with T and +00:00
        assert 'T' in result
        assert result.endswith('+00:00')
        # Should be parseable as datetime
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)

    @pytest.mark.asyncio
    async def test_utc_now_custom_format(self) -> None:
        """Test utc_now with custom format string."""
        ctx = Mock(spec=RunContext)
        custom_fmt = "%Y/%m/%d %H:%M:%S"
        input_data = NowInput(fmt=custom_fmt)
        result = await utc_now(ctx, input_data)
        # Should match the custom format (not the default, so uses strftime)
        now = datetime.now(timezone.utc)
        expected = now.strftime(custom_fmt)
        assert result == expected

    @given(a=st.floats(allow_nan=False, allow_infinity=False),
           b=st.floats(allow_nan=False, allow_infinity=False))
    @pytest.mark.asyncio
    async def test_add_numbers_commutative(self, a: float, b: float) -> None:
        """Property test: addition is commutative (a + b = b + a)."""
        ctx = Mock(spec=RunContext)
        result_ab = await add_numbers(ctx, AddInput(a=a, b=b))
        result_ba = await add_numbers(ctx, AddInput(a=b, b=a))
        assert result_ab == result_ba

    @given(a=st.floats(min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False),
           b=st.floats(min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False))
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

    @pytest.mark.asyncio
    async def test_utc_now_returns_valid_iso(self) -> None:
        """Test that utc_now returns a valid ISO 8601 datetime string."""
        ctx = Mock(spec=RunContext)
        input_data = NowInput()
        result = await utc_now(ctx, input_data)
        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(result)
        assert isinstance(parsed, datetime)
        # Should be timezone aware
        assert parsed.tzinfo is not None