"""Unit tests for tools module."""

import httpx
import pytest
from hypothesis import given, strategies as st

from agents.tools import add_numbers, utc_now, fetch_url, AddInput, NowInput, FetchInput
from pydantic_ai import RunContext


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
    async def test_fetch_url_allowed_domain(self) -> None:
        """Test fetch_url with an allowed domain."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://api.github.com/user", timeout_s=5.0)

        # Create content longer than 4096 characters
        long_content = "A" * 5000
        mock_response = Mock()
        mock_response.text = long_content
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "text/plain"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await fetch_url(ctx, input_data)

            # Content should be truncated to 4096 characters with truncation message
            expected_content = long_content[:4096] + "\n\n[Content truncated to 4096 characters]"
            assert result == expected_content

    @pytest.mark.asyncio
    async def test_fetch_url_blocked_domain(self) -> None:
        """Test fetch_url blocks non-allowed domains."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://evil.com/data")

        result = await fetch_url(ctx, input_data)

        assert result == "Refused: domain 'evil.com' not in allow-list."

    @pytest.mark.asyncio
    async def test_fetch_url_timeout(self) -> None:
        """Test fetch_url handles timeout errors."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://api.github.com/user")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            result = await fetch_url(ctx, input_data)

            assert result == "Error: Request timed out."

    @pytest.mark.asyncio
    async def test_fetch_url_http_error(self) -> None:
        """Test fetch_url handles HTTP errors."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://api.github.com/user")

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=httpx.HTTPStatusError("404", request=Mock(), response=mock_response))

            result = await fetch_url(ctx, input_data)

            assert result == "Error: HTTP 404 - Not Found"

    @pytest.mark.asyncio
    async def test_fetch_url_generic_error(self) -> None:
        """Test fetch_url handles generic exceptions."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://api.github.com/user")

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Network error"))

            result = await fetch_url(ctx, input_data)

            assert result == "Error: Network error"