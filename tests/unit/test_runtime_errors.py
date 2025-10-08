"""Unit tests for runtime module error handling."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from threading import Event
import asyncio
from typing import Any

from agents.runtime import build_agent, run_agent, run_agent_stream, StreamResult
from agents.models import AgentConfig


@pytest.fixture
def sample_agent_config() -> AgentConfig:
    """Create a sample agent configuration for testing."""
    return AgentConfig(
        name="Test Agent",
        model="openai/gpt-4-turbo",
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        top_p=0.9,
    )


@pytest.fixture
def mock_env_vars(monkeypatch) -> None:
    """Set up mock environment variables."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock_api_key_for_testing")


class TestBuildAgentErrors:
    """Test suite for build_agent error handling."""

    def test_build_agent_missing_api_key_detailed_error(self) -> None:
        """Test detailed error when OPENROUTER_API_KEY is completely missing."""
        cfg = AgentConfig(
            name="test",
            model="openai/gpt-4",
            system_prompt="Test prompt"
        )

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                build_agent(cfg)

            assert "OPENROUTER_API_KEY not set" in str(exc_info.value)

    def test_build_agent_empty_api_key_error(self) -> None:
        """Test error when OPENROUTER_API_KEY is set but empty."""
        cfg = AgentConfig(
            name="test",
            model="openai/gpt-4",
            system_prompt="Test prompt"
        )

        with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                build_agent(cfg)

            assert "OPENROUTER_API_KEY not set" in str(exc_info.value)

    @patch('agents.runtime.Agent')
    def test_build_agent_openai_client_creation_failure(self, mock_agent_class, sample_agent_config) -> None:
        """Test handling of OpenAI client creation failures."""
        # Make OpenAI constructor raise an exception
        with patch('agents.runtime.OpenAI', side_effect=Exception("OpenAI init failed")):
            with pytest.raises(Exception) as exc_info:
                build_agent(sample_agent_config)

            assert "OpenAI init failed" in str(exc_info.value)

    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    def test_build_agent_agent_creation_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of Agent creation failures."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Make Agent constructor raise an exception
        mock_agent_class.side_effect = Exception("Agent init failed")

        with pytest.raises(Exception) as exc_info:
            build_agent(sample_agent_config)

        assert "Agent init failed" in str(exc_info.value)

    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    def test_build_agent_tool_registration_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of tool registration failures."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Make tool registration raise an exception
        mock_agent_instance.tool.side_effect = Exception("Tool registration failed")

        with pytest.raises(Exception) as exc_info:
            build_agent(sample_agent_config)

        assert "Tool registration failed" in str(exc_info.value)

    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    def test_build_agent_web_tool_registration_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of web tool registration failures."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock fetch_url being available but tool registration failing
        mock_fetch_url = Mock()
        with patch("agents.runtime.fetch_url", mock_fetch_url):
            # Make tool registration fail on the third call (for fetch_url)
            mock_agent_instance.tool.side_effect = [None, None, Exception("Web tool registration failed")]

            with pytest.raises(Exception) as exc_info:
                build_agent(sample_agent_config, include_web=True)

            assert "Web tool registration failed" in str(exc_info.value)


class TestRunAgentErrors:
    """Test suite for run_agent error handling."""

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_agent_run_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of agent.run() failures."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Make agent.run raise an exception
        mock_agent_instance.run.side_effect = Exception("Agent run failed")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent(agent, "Test message")

        assert "Agent execution failed: Agent run failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_result_data_access_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of failures when accessing result.data."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock result with data access failure
        mock_result = Mock()
        mock_result.data = Mock(side_effect=AttributeError("No data attribute"))
        mock_agent_instance.run = AsyncMock(return_value=mock_result)

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent(agent, "Test message")

        assert "Agent execution failed:" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_network_timeout_error(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of network timeout errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock network timeout
        mock_agent_instance.run.side_effect = asyncio.TimeoutError("Request timed out")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent(agent, "Test message")

        assert "Agent execution failed: Request timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_api_rate_limit_error(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of API rate limit errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock rate limit error (create a custom exception class)
        class RateLimitError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.status_code = 429

        mock_agent_instance.run.side_effect = RateLimitError("Rate limit exceeded")

        agent = build_agent(sample_agent_config)

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent(agent, "Test message")

        assert "Agent execution failed:" in str(exc_info.value)


class TestRunAgentStreamErrors:
    """Test suite for run_agent_stream error handling."""

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_initial_stream_creation_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of initial stream creation failures."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Make agent.run(stream=True) fail
        mock_agent_instance.run.side_effect = Exception("Stream creation failed")

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        assert "Agent streaming failed: Stream creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_fallback_run_stream_failure(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of fallback run_stream failures."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Make run(stream=True) fail and run_stream also fail
        mock_agent_instance.run.side_effect = TypeError("stream param not supported")
        mock_agent_instance.run_stream.side_effect = Exception("run_stream failed")

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        assert "Agent streaming failed: run_stream failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_chunk_processing_error(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of errors during chunk processing."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock stream that raises exception during iteration
        async def failing_stream():
            yield Mock(delta="First chunk")
            raise Exception("Chunk processing failed")

        mock_agent_instance.run.return_value = failing_stream()

        agent = build_agent(sample_agent_config)

        deltas = []
        def on_delta(delta: str) -> None:
            deltas.append(delta)

        cancel_token = Event()

        # Should not raise - errors are logged but streaming continues gracefully
        result = await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        # Should have processed first chunk before error
        assert "First chunk" in result.text
        assert deltas == ["First chunk"]

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_context_manager_error(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test handling of context manager errors in fallback path."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Force fallback to run_stream and make context manager fail
        mock_agent_instance.run.side_effect = TypeError("stream not supported")

        # Mock failing context manager
        failing_context = AsyncMock()
        failing_context.__aenter__.side_effect = Exception("Context manager failed")
        mock_agent_instance.run_stream.return_value = failing_context

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()

        with pytest.raises(RuntimeError) as exc_info:
            await run_agent_stream(agent, "Test message", on_delta, cancel_token)

        assert "Agent streaming failed: Context manager failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_usage_conversion_dict(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test usage conversion when usage is a plain dict."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock chunk with dict usage
        mock_chunk = Mock()
        mock_chunk.delta = "Test"
        mock_chunk.response = Mock()
        mock_chunk.response.usage = {"prompt_tokens": 10, "completion_tokens": 5}

        async def mock_stream():
            yield mock_chunk

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()
        result = await run_agent_stream(agent, "Test", on_delta, cancel_token)

        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5}

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_usage_conversion_pydantic(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test usage conversion when usage is a pydantic model."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock pydantic-style usage object
        class MockUsageModel:
            def model_dump(self):
                return {"total_tokens": 100, "cost": 0.02}

        mock_chunk = Mock()
        mock_chunk.delta = "Test"
        mock_chunk.response = Mock()
        mock_chunk.response.usage = MockUsageModel()

        async def mock_stream():
            yield mock_chunk

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()
        result = await run_agent_stream(agent, "Test", on_delta, cancel_token)

        assert result.usage == {"total_tokens": 100, "cost": 0.02}

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_usage_conversion_dataclass(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test usage conversion when usage is a dataclass."""
        from dataclasses import dataclass

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        @dataclass
        class MockUsageDataclass:
            prompt_tokens: int = 20
            completion_tokens: int = 10

        mock_chunk = Mock()
        mock_chunk.delta = "Test"
        mock_chunk.response = Mock()
        mock_chunk.response.usage = MockUsageDataclass()

        async def mock_stream():
            yield mock_chunk

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()
        result = await run_agent_stream(agent, "Test", on_delta, cancel_token)

        assert result.usage == {"prompt_tokens": 20, "completion_tokens": 10}

    @pytest.mark.asyncio
    @patch('agents.runtime.Agent')
    @patch('agents.runtime.OpenAI')
    async def test_run_agent_stream_usage_conversion_fallback_to_none(self, mock_openai_class, mock_agent_class, sample_agent_config, mock_env_vars) -> None:
        """Test usage conversion fallback to None for unsupported types."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock usage object that doesn't support any conversion methods
        class UnsupportedUsage:
            def __init__(self):
                self.value = 42

        mock_chunk = Mock()
        mock_chunk.delta = "Test"
        mock_chunk.response = Mock()
        mock_chunk.response.usage = UnsupportedUsage()

        async def mock_stream():
            yield mock_chunk

        mock_agent_instance.run.return_value = mock_stream()

        agent = build_agent(sample_agent_config)

        def on_delta(delta: str) -> None:
            pass

        cancel_token = Event()
        result = await run_agent_stream(agent, "Test", on_delta, cancel_token)

        # Should fallback to None for unsupported usage type
        assert result.usage is None

