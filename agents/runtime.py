"""Runtime components for configuring and executing AI agents."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, asdict
from threading import Event
from typing import Any, Callable, Dict, Tuple

from loguru import logger
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

    logger.info(
        "Building agent",
        extra={
            "model": cfg.model,
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "include_web": include_web,
        }
    )

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


@dataclass
class StreamResult:
    """Aggregate information returned by :func:`run_agent_stream`."""

    text: str
    usage: dict[str, Any] | None
    latency_ms: int
    aborted: bool = False


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

    logger.info(
        "Starting agent execution",
        extra={
            "message_length": len(user_message),
            "agent_model": getattr(agent, 'model', 'unknown'),
        }
    )

    try:
        result = await agent.run(user_message)
        logger.info(
            "Agent execution completed successfully",
            extra={
                "response_length": len(result.data),
            }
        )
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.error(
            "Agent execution failed",
            extra={
                "error": str(exc),
            }
        )
        raise RuntimeError(f"Agent execution failed: {exc}") from exc

    return result.data, {}


async def run_agent_stream(
    agent: Agent,
    user_message: str,
    on_delta: Callable[[str], None],
    cancel_token: Event,
    correlation_id: str | None = None,
) -> StreamResult:
    """
    Fixed streaming implementation with immediate cancellation response.

    Key improvements:
    - Check cancellation before processing any chunk
    - Immediate return on cancellation without any text accumulation
    - Proper async context management for stream cleanup
    """
    logger_bound = logger.bind(correlation_id=correlation_id) if correlation_id else logger

    logger_bound.info("Starting agent streaming", extra={
        "message_length": len(user_message),
        "agent_model": getattr(agent, 'model', 'unknown'),
    })

    loop = asyncio.get_running_loop()
    start_ts = loop.time()
    text_parts: list[str] = []
    usage: dict[str, Any] | None = None
    aborted = False

    def _usage_to_dict(raw_usage: Any) -> dict[str, Any] | None:
        if raw_usage is None:
            return None
        if isinstance(raw_usage, dict):
            return dict(raw_usage)
        if hasattr(raw_usage, "model_dump"):
            return raw_usage.model_dump()
        if hasattr(raw_usage, "dict"):
            return raw_usage.dict()
        try:
            return asdict(raw_usage)
        except TypeError:
            return None

    async def _consume_stream_immediate_cancel(stream_iter: Any) -> None:
        """
        Consume stream with immediate cancellation check.

        Checks cancel_token BEFORE processing each chunk to ensure
        no partial text accumulation on cancellation.
        """
        nonlocal usage, aborted
        try:
            async for chunk in stream_iter:
                # CRITICAL FIX: Check cancellation BEFORE processing chunk
                if cancel_token.is_set():
                    aborted = True
                    logger_bound.info("Streaming cancelled before chunk processing")
                    break

                delta = getattr(chunk, "delta", None)
                if isinstance(delta, str):
                    on_delta(delta)
                    text_parts.append(delta)

                # Only update usage if we haven't been cancelled
                if not aborted:
                    response = getattr(chunk, "response", None)
                    if response is not None:
                        usage = _usage_to_dict(getattr(response, "usage", None))
        except Exception as e:
            logger_bound.error("Error during stream consumption", extra={"error": str(e)})
            raise

    # Main streaming logic with improved error handling
    try:
        stream_iterable = agent.run(user_message, stream=True)
    except TypeError:
        stream_iterable = None
    except Exception as exc:
        raise RuntimeError(f"Agent streaming failed: {exc}") from exc

    # CRITICAL FIX: Check cancellation BEFORE starting stream consumption
    if cancel_token.is_set():
        aborted = True
        logger_bound.info("Streaming cancelled before consumption started")
    else:
        if stream_iterable is not None:
            if asyncio.iscoroutine(stream_iterable):
                stream_iterable = await stream_iterable
            await _consume_stream_immediate_cancel(stream_iterable)
        else:
            try:
                stream_ctx = agent.run_stream(user_message)
            except Exception as exc:
                raise RuntimeError(f"Agent streaming failed: {exc}") from exc

            async with stream_ctx as stream_response:
                text_stream = stream_response.stream_text(delta=True)
                try:
                    async for delta_text in text_stream:
                        # CRITICAL FIX: Check cancellation BEFORE processing delta
                        if cancel_token.is_set():
                            aborted = True
                            logger_bound.info("Streaming cancelled before delta processing")
                            break
                        if delta_text:
                            on_delta(delta_text)
                            text_parts.append(delta_text)
                finally:
                    if hasattr(text_stream, "aclose"):
                        await text_stream.aclose()

                if not aborted and usage is None:
                    usage = _usage_to_dict(stream_response.usage())

    latency_ms = int((loop.time() - start_ts) * 1000)

    logger_bound.info("Agent streaming completed", extra={
        "response_length": len(text_parts),
        "latency_ms": latency_ms,
        "aborted": aborted,
        "usage_available": usage is not None,
    })

    return StreamResult("".join(text_parts), usage, latency_ms, aborted)


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
            logger.info(f"Test response: {response}")
            logger.info(f"Test usage: {usage}")
        except ValueError as error:
            logger.warning(f"Test failed: {error}")
            logger.info("Set OPENROUTER_API_KEY in .env to test")

    asyncio.run(test_agent())
