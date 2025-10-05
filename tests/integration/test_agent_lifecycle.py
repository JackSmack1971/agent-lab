"""Integration tests for complete agent lifecycle: build → run → persist workflow."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from pathlib import Path
import tempfile
import os

from agents.runtime import build_agent, run_agent_stream, StreamResult
from agents.models import AgentConfig, RunRecord
from services.persist import append_run, load_recent_runs, init_csv


@pytest.mark.integration
class TestAgentLifecycle:
    """Integration tests for complete agent build→run→persist workflow."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory for CSV testing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        return data_dir

    @pytest.fixture
    def mock_stream_response(self):
        """Mock streaming response with realistic data."""

        class MockChunk:
            def __init__(self, delta):
                self.delta = delta
                self.response = None  # type: ignore

        mock_chunk1 = MockChunk("The answer")
        mock_chunk2 = MockChunk(" is 42")
        # Last chunk includes usage data
        mock_chunk3 = MockChunk(".")

        # Create a simple object for usage that behaves like a dict
        class UsageDict(dict):
            pass

        usage_data = UsageDict(
            {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )

        # Create a mock response with usage
        mock_response = Mock()
        mock_response.usage = usage_data
        mock_chunk3.response = mock_response

        return [mock_chunk1, mock_chunk2, mock_chunk3]

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_agent_lifecycle_build_run_persist_integration(
        self,
        mock_openai_class,
        mock_agent_class,
        mock_env_vars,
        sample_agent_config,
        temp_data_dir,
        mock_stream_response,
    ):
        """Test complete agent lifecycle: build → run → persist with mocked external calls."""
        # Setup mocks
        chunks = mock_stream_response

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock streaming response
        async def mock_stream_iter():
            for chunk in chunks:
                yield chunk

        mock_agent_instance.run.return_value = mock_stream_iter()

        # Override CSV path for testing
        with patch("services.persist.CSV_PATH", temp_data_dir / "runs.csv"):
            # Phase 1: Build agent
            agent = build_agent(sample_agent_config)

            # Verify agent was built correctly
            assert agent is mock_agent_instance
            mock_openai_class.assert_called_once()
            mock_agent_class.assert_called_once()

            # Phase 2: Run agent with streaming
            collected_deltas = []

            def on_delta(delta: str):
                collected_deltas.append(delta)

            from threading import Event

            cancel_token = Event()

            result = await run_agent_stream(
                agent, "What is the answer?", on_delta, cancel_token
            )

            # Verify streaming worked
            assert isinstance(result, StreamResult)
            assert result.text == "The answer is 42."
            assert collected_deltas == ["The answer", " is 42", "."]
            assert result.aborted is False
            assert result.usage == {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            }
            assert result.latency_ms >= 0

            # Phase 3: Persist run record
            run_record = RunRecord(
                ts=datetime.now(),
                agent_name=sample_agent_config.name,
                model=sample_agent_config.model,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                latency_ms=result.latency_ms,
                cost_usd=0.001,
                streaming=True,
                model_list_source="dynamic",
                tool_web_enabled=False,
                web_status="off",
                aborted=False,
                experiment_id="lifecycle_test",
                task_label="integration_test",
            )

            append_run(run_record)

            # Phase 4: Verify persistence worked
            recent_runs = load_recent_runs(limit=5)
            assert len(recent_runs) == 1

            persisted = recent_runs[0]
            assert persisted.agent_name == sample_agent_config.name
            assert persisted.model == sample_agent_config.model
            assert persisted.prompt_tokens == 10
            assert persisted.completion_tokens == 5
            assert persisted.total_tokens == 15
            assert persisted.streaming is True
            assert persisted.experiment_id == "lifecycle_test"
            assert persisted.aborted is False

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_agent_lifecycle_with_web_tools_integration(
        self,
        mock_openai_class,
        mock_agent_class,
        mock_env_vars,
        sample_agent_config,
        temp_data_dir,
    ):
        """Test agent lifecycle with web tools enabled (mocked)."""
        # Setup mocks
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock empty stream for this test
        async def mock_empty_stream():
            return
            yield  # pragma: no cover

        mock_agent_instance.run.return_value = mock_empty_stream()

        # Mock fetch_url being available
        mock_fetch_url = Mock()
        with patch("agents.runtime.fetch_url", mock_fetch_url):
            # Build agent with web tools
            agent = build_agent(sample_agent_config, include_web=True)

            # Verify web tool was registered
            assert (
                mock_agent_instance.tool.call_count == 3
            )  # add_numbers, utc_now, fetch_url

        # Run agent (empty response for this test)
        collected_deltas = []

        def on_delta(delta: str):
            collected_deltas.append(delta)

        from threading import Event

        cancel_token = Event()

        result = await run_agent_stream(
            agent, "Test with web tools", on_delta, cancel_token
        )

        # Verify basic functionality
        assert isinstance(result, StreamResult)
        assert result.text == ""
        assert result.aborted is False

    @pytest.mark.asyncio
    @patch("agents.runtime.Agent")
    @patch("agents.runtime.OpenAI")
    async def test_agent_lifecycle_error_handling_integration(
        self,
        mock_openai_class,
        mock_agent_class,
        mock_env_vars,
        sample_agent_config,
        temp_data_dir,
    ):
        """Test agent lifecycle error handling and recovery."""
        # Setup mocks that will cause errors
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_agent_instance = Mock()
        mock_agent_class.return_value = mock_agent_instance

        # Mock agent run to raise exception
        mock_agent_instance.run.side_effect = Exception("API Error")

        with patch("services.persist.CSV_PATH", temp_data_dir / "runs.csv"):
            # Build agent successfully
            agent = build_agent(sample_agent_config)

            # Attempt to run - should handle error gracefully
            collected_deltas = []

            def on_delta(delta: str):
                collected_deltas.append(delta)

            from threading import Event

            cancel_token = Event()

            with pytest.raises(RuntimeError, match="Agent streaming failed"):
                await run_agent_stream(agent, "This will fail", on_delta, cancel_token)

            # Verify no partial data was persisted (since run failed)
            recent_runs = load_recent_runs(limit=5)
            assert len(recent_runs) == 0
