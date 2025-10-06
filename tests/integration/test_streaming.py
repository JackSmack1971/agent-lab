"""Integration tests for streaming functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from threading import Event
import asyncio
from typing import Any, AsyncGenerator

from agents.runtime import run_agent_stream, StreamResult, build_agent
from agents.models import AgentConfig


@pytest.mark.integration
class TestStreaming:
    """Integration tests for streaming and cancellation."""

    @pytest.fixture
    def mock_agent_config(self) -> AgentConfig:
        """Create a mock agent configuration."""
        return AgentConfig(
            name="Test Agent",
            model="openai/gpt-4",
            system_prompt="You are a helpful assistant."
        )

    @pytest.fixture
    def mock_env_vars(self, monkeypatch) -> None:
        """Set up mock environment variables."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "mock_api_key_for_testing")

    def test_stream_result_creation_and_defaults(self) -> None:
        """Test StreamResult dataclass creation and default values."""
        # Test with required fields
        result = StreamResult(text="Hello world", usage=None, latency_ms=100)
        assert result.text == "Hello world"
        assert result.usage is None
        assert result.latency_ms == 100
        assert result.aborted is False

        # Test with all fields
        result2 = StreamResult(
            text="Test response",
            usage={"tokens": 10},
            latency_ms=500,
            aborted=True
        )
        assert result2.text == "Test response"
        assert result2.usage == {"tokens": 10}
        assert result2.latency_ms == 500
        assert result2.aborted is True

    @pytest.mark.asyncio
    async def test_run_agent_stream_basic_successful_streaming(self, mock_agent_config, mock_env_vars) -> None:
        """Test successful streaming with basic text accumulation."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            # Create mock agent instance
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock streaming response with chunks
            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            chunks = [
                MockChunk("Hello"),
                MockChunk(" world"),
                MockChunk("!"),
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            # Build agent (this will create the mock)
            agent = build_agent(mock_agent_config)

            # Test streaming
            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

            # Verify result
            assert isinstance(result, StreamResult)
            assert result.text == "Hello world!"
            assert result.aborted is False
            assert isinstance(result.latency_ms, int)
            assert result.latency_ms >= 0
            assert result.usage is None  # No usage in this mock

            # Verify deltas were collected
            assert deltas == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_cancellation_mid_stream(self, mock_agent_config, mock_env_vars) -> None:
        """Test that streaming respects cancellation token during streaming."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock streaming with multiple chunks
            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            chunks = [
                MockChunk("First"),
                MockChunk("Second"),
                MockChunk("Third"),
                MockChunk("Fourth"),
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk
                    # Simulate some processing time
                    await asyncio.sleep(0.001)

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)
                # Cancel after receiving "Second"
                if delta == "Second":
                    cancel_token.set()

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

            # Should be aborted
            assert result.aborted is True
            # Should have partial text up to cancellation point
            assert result.text == "FirstSecond"
            # Should have collected deltas up to cancellation
            assert deltas == ["First", "Second"]
            assert isinstance(result.latency_ms, int)

    @pytest.mark.asyncio
    async def test_run_agent_stream_cancellation_before_any_chunks(self, mock_agent_config, mock_env_vars) -> None:
        """Test cancellation that occurs before any chunks are processed."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock streaming
            async def mock_stream():
                # Never yields anything due to immediate cancellation
                if False:  # pragma: no cover
                    yield None

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)

            cancel_token = Event()
            # Set cancel token immediately
            cancel_token.set()

            result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

            # Should be aborted with empty text
            assert result.aborted is True
            assert result.text == ""
            assert deltas == []
            assert isinstance(result.latency_ms, int)

    @pytest.mark.asyncio
    async def test_run_agent_stream_with_usage_metadata(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming that includes usage metadata."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock chunk with usage metadata
            class MockChunk:
                def __init__(self, delta: str, has_usage: bool = False):
                    self.delta = delta
                    if has_usage:
                        self.response = Mock()
                        self.response.usage = {"prompt_tokens": 10, "completion_tokens": 5}
                    else:
                        self.response = None

            chunks = [
                MockChunk("Hello"),
                MockChunk(" world", has_usage=True),
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

            assert result.text == "Hello world"
            assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}
            assert result.aborted is False

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_empty_deltas(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming handles empty or None deltas gracefully."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str | None):
                    self.delta = delta

            chunks = [
                MockChunk("Hello"),
                MockChunk(""),  # Empty delta
                MockChunk(None),  # None delta
                MockChunk(" world"),
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

            # Should only collect non-empty deltas
            assert result.text == "Hello world"
            assert deltas == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_run_agent_stream_fallback_to_run_stream_method(self, mock_agent_config, mock_env_vars) -> None:
        """Test fallback to run_stream method when run(stream=True) fails."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Make run(stream=True) fail
            mock_agent.run.side_effect = TypeError("stream parameter not supported")

            # Mock the stream_response object returned by the context manager
            mock_stream_response = Mock()
            mock_stream_response.usage.return_value = {"tokens": 15}

            # Mock the text stream
            class MockTextStream:
                def __init__(self, items):
                    self.items = items[:]

                def __aiter__(self):
                    return self

                async def __anext__(self):
                    if not self.items:
                        raise StopAsyncIteration
                    return self.items.pop(0)

            mock_text_stream = MockTextStream(["Hello", " from", " run_stream"])
            mock_stream_response.stream_text.return_value = mock_text_stream

            # Mock the context manager returned by run_stream
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_stream_response)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)

            mock_agent.run_stream.return_value = mock_context_manager

            agent = build_agent(mock_agent_config)

            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

            assert result.text == "Hello from run_stream"
            assert result.usage == {"tokens": 15}
            assert result.aborted is False
            assert deltas == ["Hello", " from", " run_stream"]

    @pytest.mark.asyncio
    async def test_run_agent_stream_error_handling_stream_failure(self, mock_agent_config, mock_env_vars) -> None:
        """Test error handling when streaming fails."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Make streaming fail
            mock_agent.run.side_effect = Exception("API Error")

            agent = build_agent(mock_agent_config)

            def on_delta(delta: str) -> None:
                pass  # pragma: no cover

            cancel_token = Event()

            with pytest.raises(RuntimeError, match="Agent streaming failed: API Error"):
                await run_agent_stream(agent, "Test message", on_delta, cancel_token)

    @pytest.mark.asyncio
    async def test_run_agent_stream_error_handling_run_stream_failure(self, mock_agent_config, mock_env_vars) -> None:
        """Test error handling when run_stream fails."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Make run(stream=True) fail and run_stream also fail
            mock_agent.run.side_effect = TypeError("stream not supported")
            mock_agent.run_stream.side_effect = Exception("run_stream failed")

            agent = build_agent(mock_agent_config)

            def on_delta(delta: str) -> None:
                pass  # pragma: no cover

            cancel_token = Event()

            with pytest.raises(RuntimeError, match="Agent streaming failed: run_stream failed"):
                await run_agent_stream(agent, "Test message", on_delta, cancel_token)

    @pytest.mark.asyncio
    async def test_run_agent_stream_performance_timing(self, mock_agent_config, mock_env_vars) -> None:
        """Test that latency measurement works correctly."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock fast streaming
            async def mock_stream():
                yield Mock(delta="Quick response")

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            def on_delta(delta: str) -> None:
                pass

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test", on_delta, cancel_token)

            # Latency should be a reasonable positive number
            assert isinstance(result.latency_ms, int)
            assert result.latency_ms >= 0
            # Should be very fast for this simple mock
            assert result.latency_ms < 100  # Less than 100ms

    @pytest.mark.asyncio
    async def test_run_agent_stream_handles_non_string_deltas(self, mock_agent_config, mock_env_vars) -> None:
        """Test handling of non-string delta values."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: Any):
                    self.delta = delta

            chunks = [
                MockChunk("Valid string"),
                MockChunk(123),  # Non-string delta
                MockChunk(None),  # None delta
                MockChunk(""),  # Empty string
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            deltas = []
            def on_delta(delta: str) -> None:
                deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Test", on_delta, cancel_token)

            # Should only collect valid string deltas
            assert result.text == "Valid string"
            assert deltas == ["Valid string"]