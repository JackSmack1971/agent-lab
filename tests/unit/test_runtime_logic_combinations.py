import pytest
from threading import Event
from unittest.mock import Mock, AsyncMock, patch
from agents.runtime import run_agent_stream, StreamResult, build_agent
from agents.models import AgentConfig

class TestRuntimeLogicCombinations:
    """Test all combinations of boolean conditions"""

    @pytest.mark.parametrize("cancel_set,aborted_flag,should_abort", [
        # Test truth table for cancellation logic
        (True, False, True),    # cancel_token set → abort
        (False, False, False),  # neither set → continue
        (True, True, True),     # both set → abort
        (False, True, True),    # aborted flag set → abort
    ])
    @pytest.mark.asyncio
    async def test_cancellation_logic_truth_table(
        self,
        mocker,
        cancel_set,
        aborted_flag,
        should_abort
    ):
        """
        Mutation Target: Kills boolean operator mutants in cancellation checks

        Mutants killed:
        - 'if cancel_token.is_set()' → 'if not cancel_token.is_set()'  # ✅ Fails when cancel_set=True
        - 'if not aborted' → 'if aborted'  # ✅ Fails when aborted_flag=False
        """
        # Mock agent and dependencies
        mock_agent = mocker.Mock()
        mock_stream = mocker.Mock()
        mock_agent.run_stream.return_value.__aenter__ = mocker.Mock(return_value=mock_stream)
        mock_agent.run_stream.return_value.__aexit__ = mocker.Mock(return_value=None)
        mock_stream.stream_text.return_value.__aiter__ = mocker.Mock()
        mock_stream.stream_text.return_value.__anext__ = mocker.Mock(side_effect=StopAsyncIteration)
        mock_stream.usage.return_value = None

        cancel_token = Event()
        if cancel_set:
            cancel_token.set()

        # Track if on_delta was called
        delta_calls = []
        def on_delta(delta):
            delta_calls.append(delta)

        result = await run_agent_stream(
            mock_agent,
            "test message",
            on_delta,
            cancel_token
        )

        if should_abort:
            assert result.aborted == True
        else:
            assert result.aborted == False

    @pytest.mark.parametrize("include_web,fetch_url_available,should_succeed", [
        # Test truth table for web tool inclusion
        (True, True, True),     # Both true → success
        (True, False, False),   # include_web=True but no fetch_url → fail
        (False, True, True),    # include_web=False → success regardless
        (False, False, True),   # include_web=False → success regardless
    ])
    def test_web_tool_logic_combinations(
        self,
        mocker,
        include_web,
        fetch_url_available,
        should_succeed,
        sample_agent_config
    ):
        """
        Mutation Target: Kills boolean operator mutants in web tool logic

        Mutants killed:
        - 'if include_web:' → 'if not include_web:'  # ✅ Fails when include_web=True
        - 'if fetch_url is None:' → 'if fetch_url is not None:'  # ✅ Fails when fetch_url=None
        """
        config = sample_agent_config

        if fetch_url_available:
            fetch_url_mock = mocker.Mock()
        else:
            fetch_url_mock = None

        with patch('agents.runtime.fetch_url', fetch_url_mock):
            try:
                agent = build_agent(config, include_web=include_web)
                if should_succeed:
                    assert agent is not None
                else:
                    pytest.fail("Expected RuntimeError but got success")
            except RuntimeError as e:
                if should_succeed:
                    pytest.fail(f"Expected success but got RuntimeError: {e}")
                else:
                    assert "fetch_url tool is not available" in str(e)