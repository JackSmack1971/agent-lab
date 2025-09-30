"""Runtime components for configuring and executing AI agents."""

from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from openai import OpenAI
from pydantic_ai import Agent

from agents.models import AgentConfig
from agents.tools import add_numbers, utc_now

try:  # pragma: no cover - optional tool may not be implemented yet
    from agents.tools import fetch_url
except ImportError:  # pragma: no cover - fallback when web tool absent
    fetch_url = None  # type: ignore[assignment]


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def build_agent(cfg: AgentConfig, include_web: bool = False) -> Agent:
    """Build a configured pydantic-ai Agent targeting OpenRouter.

    Parameters
    ----------
    cfg: AgentConfig
        Configuration describing the model, prompts, and sampling settings.
    include_web: bool
        When ``True``, attempts to register the optional web-fetch tool.

    Returns
    -------
    Agent
        A configured agent ready to process prompts using OpenRouter.

    Raises
    ------
    ValueError
        If the required ``OPENROUTER_API_KEY`` environment variable is missing.
    """

    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key is None:
        raise ValueError("OPENROUTER_API_KEY not set in environment")

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

    agent = Agent(
        cfg.model,
        system_prompt=cfg.system_prompt,
        model_settings={
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
        },
        openai_client=client,
    )

    agent.tool(add_numbers)
    agent.tool(utc_now)

    if include_web:
        if fetch_url is None:
            raise RuntimeError(
                "fetch_url tool is not available but include_web=True was requested"
            )
        # Web fetch tool registration is optional until implemented.
        agent.tool(fetch_url)

    return agent


async def run_agent(agent: Agent, user_message: str) -> Tuple[str, Dict[str, Any]]:
    """Execute a single-turn prompt against the provided agent.

    Parameters
    ----------
    agent: Agent
        The configured agent instance to run.
    user_message: str
        The user's message to send to the agent.

    Returns
    -------
    tuple[str, dict]
        The agent's textual response and a placeholder usage dictionary.

    Raises
    ------
    RuntimeError
        If the agent execution fails for any reason.
    """

    try:
        result = await agent.run(user_message)
    except Exception as exc:  # pragma: no cover - runtime guard
        raise RuntimeError(f"Agent execution failed: {exc}") from exc

    return result.data, {}


if __name__ == "__main__":
    import asyncio

    async def test_agent() -> None:
        cfg = AgentConfig(
            name="Test",
            model="openai/gpt-3.5-turbo",
            system_prompt="You are a helpful math assistant.",
        )

        try:
            agent = build_agent(cfg)
            response, usage = await run_agent(agent, "What is 42 + 58?")
            print(f"Response: {response}")
            print(f"Usage: {usage}")
        except ValueError as error:
            print(f"⚠️ {error}")
            print("Set OPENROUTER_API_KEY in .env to test")

    asyncio.run(test_agent())
