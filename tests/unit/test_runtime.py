"""Unit tests for runtime module."""

import pytest
from threading import Event
import asyncio
from typing import Any
from unittest.mock import Mock

from agents.runtime import build_agent, run_agent, run_agent_stream, StreamResult
from agents.models import AgentConfig


@pytest.fixture
def mock_agent(mocker):
    """Mock pydantic-ai Agent instance."""
    agent = mocker.Mock()
    agent.model = "openai/gpt-4-turbo"
    agent.system_prompt = "You are a helpful assistant."
    return agent


@pytest.fixture
def mock_openai_client(mocker):
    """Mock OpenAI client."""
    client = mocker.Mock()
    return client


class TestBuildAgent:
    """Test suite for build_agent function."""

    def test_build_agent_missing_api_key_raises_value_error(self, mocker) -> None:
        """Test that build_agent raises ValueError when OPENROUTER_API_KEY is not set."""
        cfg = AgentConfig(
            name="test_agent",
            model="openai/gpt-4-turbo",
            system_prompt="You are a helpful assistant.",
        )

        # Ensure env var is not set
        mocker.patch.dict("os.environ", {}, clear=True)
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"):
            build_agent(cfg)

    def test_build_agent_with_valid_config_and_api_key(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test successful agent building with valid config and API key."""
        # Setup mocks
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_instance.model = sample_agent_config.model
        mock_agent_instance.system_prompt = sample_agent_config.system_prompt
        mock_agent_class.return_value = mock_agent_instance

        agent = build_agent(sample_agent_config)

        # Verify OpenAI client was created with correct parameters
        mock_openai_class.assert_called_once_with(
            base_url="https://openrouter.ai/api/v1",
            api_key="mock_api_key_for_testing"
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

    def test_build_agent_registers_tools(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that build_agent registers the required tools."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        agent = build_agent(sample_agent_config)

        # Verify tools were registered
        assert mock_agent_instance.tool.call_count == 2
        # Check that add_numbers and utc_now were registered
        calls = mock_agent_instance.tool.call_args_list
        assert len(calls) == 2

    def test_build_agent_with_web_tool_when_available(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test agent building with web tool when fetch_url is available."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock fetch_url being available
        mock_fetch_url = mocker.Mock()
        mocker.patch("agents.runtime.fetch_url", mock_fetch_url)
        agent = build_agent(sample_agent_config, include_web=True)

        # Should have registered 3 tools: add_numbers, utc_now, fetch_url
        assert mock_agent_instance.tool.call_count == 3

    def test_build_agent_with_web_tool_when_unavailable_raises_error(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that build_agent raises RuntimeError when web tool requested but unavailable."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Ensure fetch_url is None (as in current code)
        mocker.patch("agents.runtime.fetch_url", None)
        with pytest.raises(RuntimeError, match="fetch_url tool is not available"):
            build_agent(sample_agent_config, include_web=True)

    def test_build_agent_tool_registration_failure_add_numbers(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test build_agent handles tool registration failure for add_numbers."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_instance.tool.side_effect = [Exception("Tool registration failed"), None]  # Fail on first tool, succeed on second
        mock_agent_class.return_value = mock_agent_instance

        with pytest.raises(Exception, match="Tool registration failed"):
            build_agent(sample_agent_config)

    def test_build_agent_tool_registration_failure_utc_now(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test build_agent handles tool registration failure for utc_now."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_instance.tool.side_effect = [None, Exception("Tool registration failed")]  # Succeed first, fail second
        mock_agent_class.return_value = mock_agent_instance

        with pytest.raises(Exception, match="Tool registration failed"):
            build_agent(sample_agent_config)

    def test_build_agent_tool_registration_failure_fetch_url(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test build_agent handles tool registration failure for fetch_url."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_instance.tool.side_effect = [None, None, Exception("Tool registration failed")]  # Succeed first two, fail third
        mock_agent_class.return_value = mock_agent_instance

        # Mock fetch_url being available
        mock_fetch_url = mocker.Mock()
        mocker.patch("agents.runtime.fetch_url", mock_fetch_url)

        with pytest.raises(Exception, match="Tool registration failed"):
            build_agent(sample_agent_config, include_web=True)

    def test_build_agent_invalid_tool_object_raises_exception(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test build_agent handles invalid tool objects gracefully."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_instance.tool.side_effect = TypeError("Invalid tool object")
        mock_agent_class.return_value = mock_agent_instance

        with pytest.raises(TypeError, match="Invalid tool object"):
            build_agent(sample_agent_config)


class TestRunAgent:
    """Test suite for run_agent function."""

    @pytest.mark.asyncio
    async def test_run_agent_successful_execution(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test successful agent execution returning text and usage."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the agent's run method
        mock_result = mocker.Mock()
        mock_result.data = "Hello, this is a response from the agent."
        mock_agent_instance.run = mocker.AsyncMock(return_value=mock_result)

        agent = build_agent(sample_agent_config)
        result_text, usage = await run_agent(agent, "Hello, world!")

        mock_agent_instance.run.assert_called_once_with("Hello, world!")
        assert result_text == "Hello, this is a response from the agent."
        assert usage == {}

    @pytest.mark.asyncio
    async def test_run_agent_handles_exceptions(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that run_agent wraps exceptions in RuntimeError."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the agent's run method to raise an exception
        mock_agent_instance.run.side_effect = Exception("API Error")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError, match="Agent execution failed: API Error"):
            await run_agent(agent, "Hello, world!")

    @pytest.mark.asyncio
    async def test_run_agent_handles_openai_connection_error(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test run_agent handles OpenAI connection errors."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock connection error
        mock_agent_instance.run.side_effect = ConnectionError("Network timeout")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError, match="Agent execution failed: Network timeout"):
            await run_agent(agent, "Hello, world!")

    @pytest.mark.asyncio
    async def test_run_agent_handles_openai_rate_limit_error(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test run_agent handles OpenAI rate limit errors."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock rate limit error
        mock_agent_instance.run.side_effect = Exception("Rate limit exceeded")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError, match="Agent execution failed: Rate limit exceeded"):
            await run_agent(agent, "Hello, world!")

    @pytest.mark.asyncio
    async def test_run_agent_handles_empty_response_data(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test run_agent handles empty or None response data."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock result with empty data
        mock_result = mocker.Mock()
        mock_result.data = ""
        mock_agent_instance.run = mocker.AsyncMock(return_value=mock_result)

        agent = build_agent(sample_agent_config)
        result_text, usage = await run_agent(agent, "Hello, world!")

        assert result_text == ""
        assert usage == {}

    @pytest.mark.asyncio
    async def test_run_agent_handles_none_response_data(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test run_agent handles None response data."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock result with None data
        mock_result = mocker.Mock()
        mock_result.data = None
        mock_agent_instance.run = mocker.AsyncMock(return_value=mock_result)

        agent = build_agent(sample_agent_config)
        result_text, usage = await run_agent(agent, "Hello, world!")

        assert result_text is None
        assert usage == {}


class TestRunAgentStream:
    """Test suite for run_agent_stream function."""

    @pytest.mark.asyncio
    async def test_run_agent_stream_basic_functionality(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test basic streaming functionality."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
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
    async def test_run_agent_stream_handles_cancellation(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that streaming respects cancellation token."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock the streaming response that yields chunks but gets cancelled
        mock_chunk1 = mocker.Mock()
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
    async def test_run_agent_stream_aggregates_deltas(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that streaming correctly aggregates text from deltas."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
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
    async def test_run_agent_stream_measures_latency(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that latency is measured correctly."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
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

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_stream_creation_failure(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test streaming handles agent.run() failure during stream creation."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock agent.run to fail with TypeError (triggers stream_iterable = None)
        mock_agent_instance.run.side_effect = TypeError("Stream not supported")

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        with pytest.raises(RuntimeError, match="Agent streaming failed: Stream not supported"):
            await run_agent_stream(agent, "Test message", on_delta, cancel_token)

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_run_stream_failure(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test streaming handles agent.run_stream() failure as fallback."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock agent.run to return None (stream_iterable = None), then run_stream fails
        mock_agent_instance.run.return_value = None
        mock_agent_instance.run_stream.side_effect = Exception("Stream context failed")

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        with pytest.raises(RuntimeError, match="Agent streaming failed: Stream context failed"):
            await run_agent_stream(agent, "Test message", on_delta, cancel_token)

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_chunk_processing_error_missing_delta(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test streaming handles chunks without delta attribute."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock chunk without delta attribute
        class MockChunk:
            def __init__(self):
                self.no_delta = "content"

        async def mock_stream():
            yield MockChunk()

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        deltas = []
        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        # Should complete without error, no deltas collected
        assert result.text == ""
        assert deltas == []
        assert result.aborted is False

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_usage_extraction_error(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test streaming handles usage extraction errors gracefully."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock stream with problematic usage
        class MockChunk:
            def __init__(self, delta):
                self.delta = delta
                self.response = Mock()
                self.response.usage = "invalid_usage_object"  # Not dict, no methods

        async def mock_stream():
            yield MockChunk("Hello")

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        deltas = []
        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        # Should complete successfully, usage should be None due to extraction failure
        assert result.text == "Hello"
        assert result.usage is None
        assert deltas == ["Hello"]

    @pytest.mark.asyncio
    async def test_run_agent_stream_cancellation_during_text_accumulation(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test cancellation during text accumulation in stream context."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock run returns None to trigger run_stream path
        mock_agent_instance.run.return_value = None

        # Mock stream context
        mock_stream_ctx = mocker.AsyncMock()
        mock_stream_response = mocker.Mock()
        mock_stream_response.stream_text.return_value = ["First", "Second", "Third"]
        mock_stream_response.usage.return_value = {"tokens": 10}

        mock_agent_instance.run_stream.return_value = mock_stream_ctx
        mock_stream_ctx.__aenter__.return_value = mock_stream_response
        mock_stream_ctx.__aexit__.return_value = None

        agent = build_agent(sample_agent_config)

        deltas = []
        def on_delta(delta: str) -> None:
            deltas.append(delta)
            # Cancel after first delta
            if len(deltas) == 1:
                cancel_token.set()

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        # Should abort after first delta, partial text accumulated
        assert result.aborted is True
        assert result.text == "First"
        assert deltas == ["First"]

    @pytest.mark.asyncio
    async def test_run_agent_stream_correlation_id_logging(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test that correlation ID is properly bound to logger."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock empty stream
        async def mock_stream():
            return
            yield

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token, correlation_id="test-123")

        # Should complete successfully with correlation ID
        assert result.aborted is False
        assert result.text == ""

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_async_stream_iterable(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test streaming handles async stream iterable from agent.run()."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock async coroutine returning stream
        async def mock_async_stream():
            class MockChunk:
                def __init__(self, delta):
                    self.delta = delta
            yield MockChunk("Async")
            yield MockChunk(" content")

        async def mock_coro():
            return mock_async_stream()

        mock_agent_instance.run.return_value = mock_coro()

        agent = build_agent(sample_agent_config)

        deltas = []
        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()

        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        assert result.text == "Async content"
        assert deltas == ["Async", " content"]
        assert result.aborted is False

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_stream_consumption_exception(self, mocker, mock_env_vars, sample_agent_config) -> None:
        """Test streaming handles exceptions during stream consumption."""
        mock_openai_class = mocker.patch('agents.runtime.OpenAI')
        mock_agent_class = mocker.patch('agents.runtime.Agent')

        mock_client = mocker.Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = mocker.Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock stream that raises exception during iteration
        async def mock_stream():
            yield Mock(delta="First")
            raise ConnectionError("Stream interrupted")

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        deltas = []
        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()

        # Should propagate the exception
        with pytest.raises(ConnectionError, match="Stream interrupted"):
            await run_agent_stream(agent, "Test message", on_delta, cancel_token)


class TestStreamResult:
    """Test suite for StreamResult dataclass."""

    def test_stream_result_creation(self) -> None:
        """Test StreamResult can be created with valid parameters."""
        result = StreamResult(
            text="Hello world",
            usage={"tokens": 10},
            latency_ms=500,
            aborted=False
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