"""Utility tools demonstrating the pydantic-ai registration pattern.

Each tool exposes a typed Pydantic schema for validation and an async
function that the agent runtime can register with pydantic-ai's
``RunContext``. This mirrors how future, more complex tools will be
implemented and validated before exposing them to user prompts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from pydantic_ai import RunContext


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
    return datetime.now(timezone.utc).strftime(input.fmt)


if __name__ == "__main__":
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
