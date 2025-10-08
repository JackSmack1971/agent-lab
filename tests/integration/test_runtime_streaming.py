"""Integration tests for runtime streaming edge cases."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from threading import Event
import asyncio
from typing import Any, AsyncGenerator, List

from agents.runtime import run_agent_stream, build_agent, StreamResult
from agents.models import AgentConfig


@pytest.mark.integration
class TestRuntimeStreamingEdgeCases:
    """Integration tests for streaming edge cases and boundary conditions."""

    @pytest.fixture
    def mock_agent_config(self) -> AgentConfig:
        """Create a mock agent configuration."""
        return AgentConfig(
            name="Edge Case Agent",
            model="openai/gpt-4",
            system_prompt="You are a helpful assistant for testing edge cases."
        )

    @pytest.fixture
    def mock_env_vars(self, monkeypatch) -> None:
        """Set up mock environment variables."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "mock_api_key_for_testing")

    @pytest.mark.asyncio
    async def test_streaming_with_extremely_large_deltas(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming with very large text chunks."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Create a very large text chunk (simulate large token outputs)
            large_text = "word " * 1000  # 5000 characters
            large_delta = large_text  # Keep trailing space to make it 5000

            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            chunks = [MockChunk(large_delta)]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)
                # Verify delta is processed immediately
                assert len(delta) >= 5000

            cancel_token = Event()
            result = await run_agent_stream(agent, "Generate large response", on_delta, cancel_token)

            assert result.text == large_delta
            assert collected_deltas == [large_delta]
            assert result.aborted is False
            assert isinstance(result.latency_ms, int)

    @pytest.mark.asyncio
    async def test_streaming_with_mixed_delta_types_and_sizes(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming with alternating large and small deltas."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            # Mix of different delta sizes
            chunks = [
                MockChunk("A"),  # Single char
                MockChunk(" very "),  # Small word
                MockChunk("large chunk of text that should be processed efficiently " * 10),  # Large chunk
                MockChunk("."),  # Single punctuation
                MockChunk("Final"),  # Normal word
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Mixed content test", on_delta, cancel_token)

            expected_text = "".join(chunk.delta for chunk in chunks)
            assert result.text == expected_text
            assert collected_deltas == [chunk.delta for chunk in chunks]
            assert result.aborted is False

    @pytest.mark.asyncio
    async def test_streaming_with_unicode_and_special_characters(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming with Unicode characters and special symbols."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            # Unicode and special characters
            unicode_chunks = [
                MockChunk("Hello 🌟 "),
                MockChunk("café "),
                MockChunk("naïve "),
                MockChunk("测试 "),
                MockChunk("🚀✨"),
                MockChunk("α + β = γ"),
            ]

            async def mock_stream():
                for chunk in unicode_chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Unicode test", on_delta, cancel_token)

            expected_text = "".join(chunk.delta for chunk in unicode_chunks)
            assert result.text == expected_text
            assert collected_deltas == [chunk.delta for chunk in unicode_chunks]
            assert result.aborted is False

    @pytest.mark.asyncio
    async def test_streaming_with_empty_chunks_interspersed(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming with empty string deltas mixed in."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            # Mix empty and non-empty chunks
            chunks = [
                MockChunk("Start"),
                MockChunk(""),  # Empty
                MockChunk(" "),  # Space
                MockChunk(""),  # Another empty
                MockChunk("middle"),
                MockChunk(""),  # Empty
                MockChunk(" end"),
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Empty chunks test", on_delta, cancel_token)

            expected_text = "".join(chunk.delta for chunk in chunks)
            assert result.text == expected_text
            assert collected_deltas == [chunk.delta for chunk in chunks]
            assert result.aborted is False

    @pytest.mark.asyncio
    async def test_streaming_with_rapid_cancellation_during_processing(self, mock_agent_config, mock_env_vars) -> None:
        """Test cancellation that occurs during chunk processing."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str, delay: float = 0.001):
                    self.delta = delta
                    self.delay = delay

            chunks = [
                MockChunk("First ", 0.01),
                MockChunk("Second ", 0.01),
                MockChunk("Third ", 0.01),
                MockChunk("Fourth ", 0.01),
                MockChunk("Fifth ", 0.01),
            ]

            async def mock_stream():
                for chunk in chunks:
                    await asyncio.sleep(chunk.delay)  # Simulate processing time
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            cancel_token = Event()

            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)
                # Cancel after receiving "Second "
                if delta == "Second ":
                    cancel_token.set()

            result = await run_agent_stream(agent, "Rapid cancel test", on_delta, cancel_token)

            # Should have partial results up to cancellation point
            assert result.aborted is True
            assert "First " in result.text
            assert "Second " in result.text
            # Should not have processed chunks after cancellation
            assert "Third " not in result.text
            assert len(collected_deltas) <= 3  # First, Second, maybe Third if timing

    @pytest.mark.asyncio
    async def test_streaming_with_coroutine_stream_creation(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming when agent.run returns a coroutine that yields a stream."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            chunks = [
                MockChunk("Async "),
                MockChunk("stream "),
                MockChunk("creation"),
            ]

            async def mock_coro_stream():
                for chunk in chunks:
                    yield chunk

            # Make run return a coroutine that returns the stream
            async def mock_run_coroutine(*args, **kwargs):
                return mock_coro_stream()

            mock_agent.run = mock_run_coroutine

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Coroutine test", on_delta, cancel_token)

            expected_text = "".join(chunk.delta for chunk in chunks)
            assert result.text == expected_text
            assert collected_deltas == [chunk.delta for chunk in chunks]
            assert result.aborted is False

    @pytest.mark.asyncio
    async def test_streaming_with_multiple_usage_updates(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming with usage data updated in multiple chunks."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str, usage_data: dict | None = None):
                    self.delta = delta
                    if usage_data:
                        self.response = Mock()
                        self.response.usage = usage_data
                    else:
                        self.response = None

            chunks = [
                MockChunk("First ", {"tokens": 1}),
                MockChunk("Second ", {"tokens": 2}),  # Later usage should override
                MockChunk("Third", {"tokens": 3}),
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Usage test", on_delta, cancel_token)

            assert result.text == "First Second Third"
            # Should have the last usage data
            assert result.usage == {"tokens": 3}
            assert result.aborted is False

    @pytest.mark.asyncio
    async def test_streaming_with_run_stream_context_manager_error_recovery(self, mock_agent_config, mock_env_vars) -> None:
        """Test fallback behavior when run_stream context manager fails."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Force run(stream=True) to fail, then make run_stream fail too
            mock_agent.run.side_effect = TypeError("stream param not supported")

            # Mock failing context manager
            failing_context = AsyncMock()
            failing_context.__aenter__.side_effect = Exception("Context manager error")
            mock_agent.run_stream.return_value = failing_context

            agent = build_agent(mock_agent_config)

            def on_delta(delta: str) -> None:
                pass

            cancel_token = Event()

            with pytest.raises(RuntimeError) as exc_info:
                await run_agent_stream(agent, "Context manager test", on_delta, cancel_token)

            assert "Agent streaming failed: Context manager error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_streaming_with_async_context_manager_aclose_handling(self, mock_agent_config, mock_env_vars) -> None:
        """Test proper cleanup of async context manager with aclose."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Force fallback to run_stream
            mock_agent.run.side_effect = TypeError("stream not supported")

            # Mock stream response with aclose method
            mock_stream_response = Mock()
            mock_stream_response.usage.return_value = {"final_tokens": 42}

            # Mock text stream with aclose
            mock_text_stream = AsyncMock()
            mock_text_stream.__aiter__ = Mock(return_value=mock_text_stream)
            mock_text_stream.__anext__ = AsyncMock(side_effect=[
                "Context ", "manager ", "cleanup"
            ] + [StopAsyncIteration()])
            mock_text_stream.aclose = AsyncMock()

            mock_stream_response.stream_text.return_value = mock_text_stream

            # Mock context manager
            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_stream_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_agent.run_stream.return_value = mock_context

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            result = await run_agent_stream(agent, "Context cleanup test", on_delta, cancel_token)

            assert result.text == "Context manager cleanup"
            assert result.usage == {"final_tokens": 42}
            assert collected_deltas == ["Context ", "manager ", "cleanup"]

            # Verify aclose was called for cleanup
            mock_text_stream.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_with_exception_in_on_delta_callback(self, mock_agent_config, mock_env_vars) -> None:
        """Test handling of exceptions thrown in the on_delta callback."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            chunks = [
                MockChunk("First "),
                MockChunk("Second "),  # Exception will be raised here
                MockChunk("Third "),   # This should not be processed
            ]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_deltas = []
            def failing_on_delta(delta: str) -> None:
                if delta == "Second ":
                    raise ValueError("Callback error")
                collected_deltas.append(delta)

            cancel_token = Event()

            # The streaming should continue despite callback errors
            result = await run_agent_stream(agent, "Callback error test", failing_on_delta, cancel_token)

            # Should have processed first chunk, failed on second, but text accumulation continues
            assert "First " in result.text
            assert collected_deltas == ["First "]  # Only first delta collected due to exception
            assert result.aborted is False  # Should not abort due to callback error

    @pytest.mark.asyncio
    async def test_streaming_with_memory_pressure_simulation(self, mock_agent_config, mock_env_vars) -> None:
        """Test streaming behavior under simulated memory pressure (many small chunks)."""
        with patch('agents.runtime.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Create many small chunks to simulate memory pressure
            num_chunks = 1000
            chunks = [Mock(delta=f"chunk{i} ") for i in range(num_chunks)]

            async def mock_stream():
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            agent = build_agent(mock_agent_config)

            collected_count = 0
            def counting_on_delta(delta: str) -> None:
                nonlocal collected_count
                collected_count += 1

            cancel_token = Event()
            result = await run_agent_stream(agent, "Memory pressure test", counting_on_delta, cancel_token)

            # Verify all chunks were processed
            assert collected_count == num_chunks
            expected_text = "".join(f"chunk{i} " for i in range(num_chunks))
            assert result.text == expected_text
            assert result.aborted is False
            assert isinstance(result.latency_ms, int)