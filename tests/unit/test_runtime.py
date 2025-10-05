"""Unit tests for runtime module."""

import asyncio
from threading import Event
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agents.models import AgentConfig
from agents.runtime import StreamResult, build_agent, run_agent, run_agent_stream


@pytest.fixture
def mock_agent():
    """Mock pydantic-ai Agent instance."""
    agent = Mock()
    agent.model = "openai/gpt-4-turbo"
    agent.system_prompt = "You are a helpful assistant."
    return agent


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = Mock()
    return client


class TestBuildAgent:
    """Test suite for build_agent function."""

    def test_build_agent_missing_api_key_raises_value_error(self) -> None:
        """Test that build_agent raises ValueError when OPENROUTER_API_KEY is not set."""
        cfg = AgentConfig(
            name="test_agent",
            model="openai/gpt-4-turbo",
            system_prompt="You are a helpful assistant.",
        )

        # Ensure env var is not set
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"):
                build_agent(cfg)

    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    def test_build_agent_with_valid_config_and_api_key(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test successful agent building with valid config and API key."""
        # Setup mocks
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_instance.model = sample_agent_config.model
        mock_agent_instance.system_prompt = sample_agent_config.system_prompt
        mock_agent_class.return_value = mock_agent_instance

        agent = build_agent(sample_agent_config)

        # Verify OpenAI client was created with correct parameters
        mock_openai_class.assert_called_once_with(
            base_url="https://openrouter.ai/api/v1", api_key="mock_api_key_for_testing"
        )

        # Verify Agent was created with correct parameters
        mock_agent_class.assert_called_once_with(
            sample_agent_config.model,
            system_prompt=sample_agent_config.system_prompt,
            model_settings={
                "temperature": sample_agent_config.temperature,
                "top_p": sample_agent_config.top_p,
            },
            openai_client=mock_client,
        )

        # Verify tools were registered
        assert mock_agent_instance.tool.call_count == 2  # add_numbers and utc_now

        assert agent is mock_agent_instance

    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    def test_build_agent_registers_tools(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test that build_agent registers the required tools."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        agent = build_agent(sample_agent_config)

        # Verify tools were registered
        assert mock_agent_instance.tool.call_count == 2
        # Check that add_numbers and utc_now were registered
        calls = mock_agent_instance.tool.call_args_list
        assert len(calls) == 2

    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    def test_build_agent_with_web_tool_when_available(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test agent building with web tool when fetch_url is available."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock fetch_url being available
        mock_fetch_url = Mock()
        with patch("agents.runtime.fetch_url", mock_fetch_url):
            agent = build_agent(sample_agent_config, include_web=True)

        # Should have registered 3 tools: add_numbers, utc_now, fetch_url
        assert mock_agent_instance.tool.call_count == 3

    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    def test_build_agent_with_web_tool_when_unavailable_raises_error(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test that build_agent raises RuntimeError when web tool requested but unavailable."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Ensure fetch_url is None (as in current code)
        with patch("agents.runtime.fetch_url", None):
            with pytest.raises(RuntimeError, match="fetch_url tool is not available"):
                build_agent(sample_agent_config, include_web=True)


class TestRunAgent:
    """Test suite for run_agent function."""

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_run_agent_successful_execution(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test successful agent execution returning text and usage."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the agent's run method
        mock_result = Mock()
        mock_result.data = "Hello, this is a response from the agent."
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        agent = build_agent(sample_agent_config)
        result_text, usage = await run_agent(agent, "Hello, world!")

        mock_agent_instance.run.assert_called_once_with("Hello, world!")
        assert result_text == "Hello, this is a response from the agent."
        assert usage == {}

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_run_agent_handles_exceptions(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test that run_agent wraps exceptions in RuntimeError."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the agent's run method to raise an exception
        mock_agent_instance.run.side_effect = Exception("API Error")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError, match="Agent execution failed: API Error"):
            await run_agent(agent, "Hello, world!")


class TestRunAgentStream:
    """Test suite for run_agent_stream function."""

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_run_agent_stream_basic_functionality(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test basic streaming functionality."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the streaming response
        class MockChunk:
            def __init__(self, delta):
                self.delta = delta

        mock_chunk1 = MockChunk("Hello")
        mock_chunk2 = MockChunk(" world")
        mock_chunk3 = MockChunk("!")

        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        deltas = []

        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        assert isinstance(result, StreamResult)
        assert result.text == "Hello world!"
        assert isinstance(result.latency_ms, int)
        assert result.aborted is False
        assert result.usage is None

        # Verify deltas were collected
        assert deltas == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_run_agent_stream_handles_cancellation(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test that streaming respects cancellation token."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the streaming response that yields chunks but gets cancelled
        mock_chunk1 = Mock()
        mock_chunk1.delta = "Hello"

        async def mock_stream():
            yield mock_chunk1
            # Simulate cancellation check - this won't be reached due to immediate cancel

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        deltas = []

        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()
        # Set cancel token immediately to test cancellation
        cancel_token.set()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        assert isinstance(result, StreamResult)
        assert result.aborted is True
        # Should have empty text since cancelled before any processing
        assert result.text == ""

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_run_agent_stream_aggregates_deltas(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test that streaming correctly aggregates text from deltas."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock streaming with deltas
        class MockChunk:
            def __init__(self, delta):
                self.delta = delta

        mock_chunk1 = MockChunk("The")
        mock_chunk2 = MockChunk(" quick")
        mock_chunk3 = MockChunk(" brown")

        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        collected_deltas = []

        def on_delta(delta: str) -> None:
            collected_deltas.append(delta)

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        # The full text should equal joined deltas
        assert result.text == "The quick brown"
        assert collected_deltas == ["The", " quick", " brown"]

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_run_agent_stream_measures_latency(
        self, mock_openai_class, mock_agent_class, mock_env_vars, sample_agent_config
    ) -> None:
        """Test that latency is measured correctly."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock empty stream for latency test
        async def mock_stream():
            return
            yield  # pragma: no cover

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        # Latency should be a reasonable positive number
        assert result.latency_ms >= 0
        assert isinstance(result.latency_ms, int)


class TestStreamResult:
    """Test suite for StreamResult dataclass."""

    def test_stream_result_creation(self) -> None:
        """Test StreamResult can be created with valid parameters."""
        result = StreamResult(
            text="Hello world", usage={"tokens": 10}, latency_ms=500, aborted=False
        )

        assert result.text == "Hello world"
        assert result.usage == {"tokens": 10}
        assert result.latency_ms == 500
        assert result.aborted is False

    def test_stream_result_defaults(self) -> None:
        """Test StreamResult default values."""
        result = StreamResult(text="test", usage=None, latency_ms=100)

        assert result.aborted is False
        assert result.usage is None
        assert result.text == "test"
        assert result.latency_ms == 100
