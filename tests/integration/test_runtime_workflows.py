"""Integration tests for complete runtime workflows."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from threading import Event
import asyncio
from typing import Any, Dict, List

from agents.runtime import build_agent, run_agent, run_agent_stream, StreamResult
from agents.models import AgentConfig


@pytest.mark.integration
class TestRuntimeWorkflows:
    """Integration tests for complete runtime workflows combining multiple functions."""

    @pytest.fixture
    def workflow_agent_config(self) -> AgentConfig:
        """Create a comprehensive agent configuration for workflow testing."""
        return AgentConfig(
            name="Workflow Test Agent",
            model="openai/gpt-4-turbo",
            system_prompt="You are a comprehensive test assistant.",
            temperature=0.7,
            top_p=0.9,
        )

    @pytest.fixture
    def mock_env_vars(self, monkeypatch) -> None:
        """Set up mock environment variables."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "mock_api_key_for_workflow_testing")

    @pytest.mark.asyncio
    async def test_complete_agent_lifecycle_workflow(self, workflow_agent_config, mock_env_vars) -> None:
        """Test complete agent lifecycle: build -> run -> stream -> cleanup."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            # Setup mocks
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Mock successful agent building
            agent = build_agent(workflow_agent_config)

            # Test 1: Regular run_agent
            mock_result = Mock()
            mock_result.data = "Regular response"
            mock_agent.run = AsyncMock(return_value=mock_result)

            response, usage = await run_agent(agent, "Test query")
            assert response == "Regular response"
            assert usage == {}

            # Test 2: Streaming with same agent
            class MockChunk:
                def __init__(self, delta: str, usage: dict | None = None):
                    self.delta = delta
                    if usage:
                        self.response = Mock()
                        self.response.usage = usage
                    else:
                        self.response = None

            stream_chunks = [
                MockChunk("Streaming "),
                MockChunk("response ", {"tokens": 15}),
                MockChunk("complete"),
            ]

            async def mock_stream():
                for chunk in stream_chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            collected_deltas = []
            def on_delta(delta: str) -> None:
                collected_deltas.append(delta)

            cancel_token = Event()
            stream_result = await run_agent_stream(agent, "Stream test", on_delta, cancel_token)

            assert stream_result.text == "Streaming response complete"
            assert stream_result.usage == {"tokens": 15}
            assert collected_deltas == ["Streaming ", "response ", "complete"]
            assert stream_result.aborted is False

    @pytest.mark.asyncio
    async def test_agent_reuse_across_multiple_operations(self, workflow_agent_config, mock_env_vars) -> None:
        """Test reusing the same agent instance for multiple operations."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            agent = build_agent(workflow_agent_config)

            # Multiple run_agent calls
            responses = []
            for i in range(3):
                mock_result = Mock()
                mock_result.data = f"Response {i+1}"
                mock_agent.run = AsyncMock(return_value=mock_result)

                response, usage = await run_agent(agent, f"Query {i+1}")
                responses.append(response)

            assert responses == ["Response 1", "Response 2", "Response 3"]

            # Verify agent.run was called 3 times
            assert mock_agent.run.call_count == 3

    @pytest.mark.asyncio
    async def test_mixed_workflow_with_error_recovery(self, workflow_agent_config, mock_env_vars) -> None:
        """Test workflow that mixes successful operations with error recovery."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            agent = build_agent(workflow_agent_config)

            # Successful operation
            mock_result = Mock()
            mock_result.data = "Success response"
            mock_agent.run = AsyncMock(return_value=mock_result)

            response1, usage1 = await run_agent(agent, "Success query")
            assert response1 == "Success response"

            # Failed operation with recovery
            mock_agent.run.side_effect = Exception("Temporary failure")

            with pytest.raises(RuntimeError):
                await run_agent(agent, "Failed query")

            # Recovery operation
            mock_agent.run.side_effect = None  # Reset
            mock_result.data = "Recovery response"
            mock_agent.run = AsyncMock(return_value=mock_result)

            response2, usage2 = await run_agent(agent, "Recovery query")
            assert response2 == "Recovery response"

    @pytest.mark.asyncio
    async def test_concurrent_operations_workflow(self, workflow_agent_config, mock_env_vars) -> None:
        """Test running multiple operations concurrently with the same agent."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            agent = build_agent(workflow_agent_config)

            # Mock streaming responses
            class MockChunk:
                def __init__(self, delta: str, op_id: int):
                    self.delta = delta
                    self.op_id = op_id

            async def create_mock_stream(op_id: int):
                chunks = [
                    MockChunk(f"Op{op_id}-Part1 ", op_id),
                    MockChunk(f"Op{op_id}-Part2 ", op_id),
                    MockChunk(f"Op{op_id}-Complete", op_id),
                ]
                for chunk in chunks:
                    await asyncio.sleep(0.001)  # Small delay to simulate real streaming
                    yield chunk

            # Concurrent streaming operations
            async def run_streaming_operation(op_id: int):
                collected = []
                def on_delta(delta: str):
                    collected.append(delta)

                # Set up mock for this specific operation
                mock_agent.run.return_value = create_mock_stream(op_id)

                cancel_token = Event()
                result = await run_agent_stream(agent, f"Concurrent op {op_id}", on_delta, cancel_token)
                return result, collected

            # Run 3 concurrent operations
            tasks = [run_streaming_operation(i) for i in range(1, 4)]
            results = await asyncio.gather(*tasks)

            # Verify all operations completed successfully
            for i, (result, collected) in enumerate(results, 1):
                assert isinstance(result, StreamResult)
                assert result.aborted is False
                assert result.text == f"Op{i}-Part1 Op{i}-Part2 Op{i}-Complete"
                assert collected == [f"Op{i}-Part1 ", f"Op{i}-Part2 ", f"Op{i}-Complete"]

    @pytest.mark.asyncio
    async def test_workflow_with_cancellation_and_recovery(self, workflow_agent_config, mock_env_vars) -> None:
        """Test workflow involving cancellation followed by successful recovery."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            agent = build_agent(workflow_agent_config)

            # First operation: successful streaming
            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            async def mock_successful_stream():
                chunks = [MockChunk("Success "), MockChunk("response")]
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_successful_stream()

            collected1 = []
            def on_delta1(delta: str):
                collected1.append(delta)

            cancel_token1 = Event()
            result1 = await run_agent_stream(agent, "Success test", on_delta1, cancel_token1)

            assert result1.text == "Success response"
            assert not result1.aborted

            # Second operation: cancelled streaming
            async def mock_cancellable_stream():
                yield MockChunk("Before ")
                yield MockChunk("cancel")

            mock_agent.run.return_value = mock_cancellable_stream()

            collected2 = []
            cancel_token2 = Event()

            def on_delta2(delta: str):
                collected2.append(delta)
                if delta == "Before ":
                    cancel_token2.set()  # Cancel immediately

            result2 = await run_agent_stream(agent, "Cancel test", on_delta2, cancel_token2)

            assert result2.aborted is True
            assert result2.text == "Before "

            # Third operation: recovery after cancellation
            async def mock_recovery_stream():
                chunks = [MockChunk("Recovery "), MockChunk("successful")]
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_recovery_stream()

            collected3 = []
            def on_delta3(delta: str):
                collected3.append(delta)

            cancel_token3 = Event()
            result3 = await run_agent_stream(agent, "Recovery test", on_delta3, cancel_token3)

            assert result3.text == "Recovery successful"
            assert not result3.aborted

    @pytest.mark.asyncio
    async def test_workflow_with_different_models_and_configs(self, mock_env_vars) -> None:
        """Test workflow using different agent configurations."""
        configs = [
            AgentConfig(name="GPT-4", model="openai/gpt-4", system_prompt="You are GPT-4"),
            AgentConfig(name="GPT-3.5", model="openai/gpt-3.5-turbo", system_prompt="You are GPT-3.5"),
            AgentConfig(name="Claude", model="anthropic/claude-3", system_prompt="You are Claude"),
        ]

        results = []

        for config in configs:
            with patch('agents.runtime.Agent') as mock_agent_class, \
                 patch('agents.runtime.OpenAI') as mock_openai_class:

                mock_client = Mock()
                mock_openai_class.return_value = mock_client

                mock_agent = Mock()
                mock_agent_class.return_value = mock_agent

                agent = build_agent(config)

                # Mock response specific to model
                mock_result = Mock()
                mock_result.data = f"Response from {config.model}"
                mock_agent.run = AsyncMock(return_value=mock_result)

                response, usage = await run_agent(agent, f"Test with {config.name}")
                results.append((config.name, response))

        expected = [
            ("GPT-4", "Response from openai/gpt-4"),
            ("GPT-3.5", "Response from openai/gpt-3.5-turbo"),
            ("Claude", "Response from anthropic/claude-3"),
        ]
        assert results == expected

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_with_web_tools(self, workflow_agent_config, mock_env_vars) -> None:
        """Test complete workflow including web tool functionality."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class, \
             patch('agents.runtime.fetch_url') as mock_fetch_url:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            # Build agent with web tools
            agent = build_agent(workflow_agent_config, include_web=True)

            # Verify web tool was registered
            assert mock_agent.tool.call_count == 3  # add_numbers, utc_now, fetch_url

            # Mock successful web-enabled operation
            mock_result = Mock()
            mock_result.data = "Web-enhanced response with fetched data"
            mock_agent.run = AsyncMock(return_value=mock_result)

            response, usage = await run_agent(agent, "Query requiring web access")
            assert response == "Web-enhanced response with fetched data"

    @pytest.mark.asyncio
    async def test_performance_workflow_under_load(self, workflow_agent_config, mock_env_vars) -> None:
        """Test workflow performance under simulated load."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            agent = build_agent(workflow_agent_config)

            # Simulate high-frequency operations
            operations = 50

            async def run_operation(i: int):
                mock_result = Mock()
                mock_result.data = f"Response {i}"
                mock_agent.run = AsyncMock(return_value=mock_result)

                start_time = asyncio.get_event_loop().time()
                response, usage = await run_agent(agent, f"Query {i}")
                end_time = asyncio.get_event_loop().time()

                return response, end_time - start_time

            # Run operations concurrently
            tasks = [run_operation(i) for i in range(operations)]
            results = await asyncio.gather(*tasks)

            # Verify all operations completed
            assert len(results) == operations
            for i, (response, duration) in enumerate(results):
                assert response == f"Response {i}"
                assert duration >= 0  # Should have taken some time

    @pytest.mark.asyncio
    async def test_workflow_state_consistency_across_operations(self, workflow_agent_config, mock_env_vars) -> None:
        """Test that agent state remains consistent across multiple operations."""
        with patch('agents.runtime.Agent') as mock_agent_class, \
             patch('agents.runtime.OpenAI') as mock_openai_class:

            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            mock_agent = Mock()
            mock_agent_class.return_value = mock_agent

            agent = build_agent(workflow_agent_config)

            # Track operation sequence
            operation_log = []

            # Operation 1: Regular run
            mock_result1 = Mock()
            mock_result1.data = "First response"
            mock_agent.run = AsyncMock(return_value=mock_result1)

            response1, _ = await run_agent(agent, "First query")
            operation_log.append(("run_agent", response1))

            # Operation 2: Streaming
            class MockChunk:
                def __init__(self, delta: str):
                    self.delta = delta

            async def mock_stream():
                chunks = [MockChunk("Stream "), MockChunk("response")]
                for chunk in chunks:
                    yield chunk

            mock_agent.run.return_value = mock_stream()

            collected = []
            def on_delta(delta: str):
                collected.append(delta)

            cancel_token = Event()
            result2 = await run_agent_stream(agent, "Second query", on_delta, cancel_token)
            operation_log.append(("run_agent_stream", result2.text))

            # Operation 3: Another regular run
            mock_result3 = Mock()
            mock_result3.data = "Third response"
            mock_agent.run = AsyncMock(return_value=mock_result3)

            response3, _ = await run_agent(agent, "Third query")
            operation_log.append(("run_agent", response3))

            # Verify sequence and consistency
            expected_log = [
                ("run_agent", "First response"),
                ("run_agent_stream", "Stream response"),
                ("run_agent", "Third response"),
            ]
            assert operation_log == expected_log