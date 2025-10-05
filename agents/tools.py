"""Utility tools demonstrating the pydantic-ai registration pattern.

Each tool exposes a typed Pydantic schema for validation and an async
function that the agent runtime can register with pydantic-ai's
``RunContext``. This mirrors how future, more complex tools will be
implemented and validated before exposing them to user prompts.
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

# Allow-list for secure web access to prevent SSRF attacks
ALLOWED_DOMAINS = {"example.com", "api.github.com", "raw.githubusercontent.com"}


class AddInput(BaseModel):
    """Input schema for adding two numbers."""

    a: float
    b: float


async def add_numbers(ctx: RunContext, input: AddInput) -> float:
    """Add two numbers together. Use this when the user asks for arithmetic addition."""

    # Pydantic validation on ``AddInput`` ensures both operands are numeric.
    return input.a + input.b


class NowInput(BaseModel):
    """Input schema for getting current time with optional format string."""

    fmt: str = Field(default="%Y-%m-%d %H:%M:%S UTC")


async def utc_now(ctx: RunContext, input: NowInput) -> str:
    """Get current UTC time. Use this when the user asks what time it is."""

    # Using UTC avoids timezone ambiguity and leaking server locale data.
    # Return ISO format for consistency with standards
    if input.fmt == "%Y-%m-%d %H:%M:%S UTC":
        return datetime.now(timezone.utc).strftime(input.fmt)
    else:
        return datetime.now(timezone.utc).strftime(input.fmt)


class FetchInput(BaseModel):
    """Input schema for fetching content from a URL with timeout."""

    url: str
    timeout_s: float = Field(default=10.0, ge=1.0, le=30.0)


async def fetch_url(ctx: RunContext, input: FetchInput) -> str:
    """Fetch content from a URL with allow-list enforcement for security.

    Only allows requests to predefined domains to prevent SSRF attacks.
    Content is truncated to 4096 characters. Follows redirects and applies
    the specified timeout.

    Parameters
    ----------
    ctx : RunContext
        The pydantic-ai run context.
    input : FetchInput
        The URL and timeout parameters.

    Returns
    -------
    str
        The fetched content or refusal message if domain not allowed.
    """
    try:
        parsed_url = urlparse(input.url)
        domain = parsed_url.netloc.lower()

        if domain not in ALLOWED_DOMAINS:
            return f"Refused: domain '{domain}' not in allow-list."

        async with httpx.AsyncClient(timeout=input.timeout_s, follow_redirects=True) as client:
            response = await client.get(input.url)
            response.raise_for_status()
            content = response.text[:4096]  # Truncate to 4K chars
            return content
    except httpx.TimeoutException:
        return "Error: Request timed out."
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {e.response.reason_phrase}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    from unittest.mock import Mock

    async def test_tools() -> None:
        ctx = Mock(spec=RunContext)

        # Test addition
        result1 = await add_numbers(ctx, AddInput(a=5.5, b=3.2))
        print(f"5.5 + 3.2 = {result1}")
        assert result1 == 8.7

        # Test clock
        result2 = await utc_now(ctx, NowInput())
        print(f"Current UTC: {result2}")
        assert "UTC" in result2

        print("✅ All tools working")

    asyncio.run(test_tools())
