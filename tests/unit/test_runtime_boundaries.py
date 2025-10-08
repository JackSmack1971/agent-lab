import pytest
from agents.models import AgentConfig
from agents.runtime import build_agent, run_agent

class TestRuntimeBoundaryConditions:
    """Tests specifically designed to kill boundary mutants"""

    @pytest.mark.parametrize("user_message_length,should_fail", [
        (0, False),      # Empty message - should work (agent handles empty input)
        (1, False),      # Minimal message
        (1000, False),   # Large message
    ])
    @pytest.mark.asyncio
    async def test_user_message_length_boundaries(self, user_message_length, should_fail, mocker):
        """
        Mutation Target: Kills mutants that change len() comparisons

        Example mutant killed:
        - Original: if len(user_message) > 0
        - Mutant: if len(user_message) >= 0  # ✅ This test with empty string kills it
        """
        message = "a" * user_message_length

        # Mock the agent to avoid API calls
        mock_agent = mocker.Mock()
        mock_result = mocker.Mock()
        mock_result.data = "response"
        mock_agent.run.return_value = mock_result

        with mocker.patch('agents.runtime.Agent', return_value=mock_agent):
            try:
                result, usage = await run_agent(mock_agent, message)
                if should_fail:
                    pytest.fail("Expected failure but got success")
                else:
                    assert result == "response"
            except Exception:
                if not should_fail:
                    raise

    @pytest.mark.parametrize("temperature", [
        -0.01,   # Just below zero
        0.0,     # Exact zero
        0.01,    # Just above zero
        1.99,    # Just below 2.0
        2.0,     # Exact boundary
        2.01,    # Just above 2.0
    ])
    def test_temperature_validation_precise(self, temperature):
        """
        Mutation Target: Boundary comparison mutants

        Kills mutants like:
        - temp > 2.0 → temp >= 2.0
        - temp >= 0.0 → temp > 0.0
        """
        from pydantic import ValidationError

        if temperature < 0.0 or temperature > 2.0:
            with pytest.raises(ValidationError):
                AgentConfig(name="test", model="gpt-4", system_prompt="test", temperature=temperature)
        else:
            config = AgentConfig(name="test", model="gpt-4", system_prompt="test", temperature=temperature)
            assert config.temperature == temperature